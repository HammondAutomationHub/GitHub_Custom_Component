"""Coordinator that checks GitHub and optionally installs updates."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import tempfile

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CHECK_INTERVALS,
    CONF_BRANCH,
    CONF_CHECK_INTERVAL,
    CONF_FOLDER,
    CONF_REPO,
    CONF_TOKEN,
    CONF_UPDATE_MODE,
    DOMAIN,
    ISSUE_RESTART,
    NOTIFICATION_RESTART,
    STORAGE_VERSION,
    UPDATE_MODE_AUTOMATIC,
)
from .errors import GPMError, InvalidAuth
from .github_client import GitHubClient
from .installer import install_archive, read_local_version
from .policy import persisted_state
from .repo import normalize_branch, split_slug
from .updater import Evaluation, evaluate_update, in_sync_displays, status_attributes

_LOGGER = logging.getLogger(__name__)


class GPMStatus:
    """State exposed to entities."""

    def __init__(
        self,
        *,
        installed_sha: str | None,
        remote_sha: str,
        installed_display: str,
        latest_display: str,
        commit_message: str,
        update_available: bool,
        local_version: str,
        remote_version: str,
    ) -> None:
        self.installed_sha = installed_sha
        self.remote_sha = remote_sha
        self.installed_display = installed_display
        self.latest_display = latest_display
        self.commit_message = commit_message
        self.update_available = update_available
        self.local_version = local_version
        self.remote_version = remote_version


class GPMCoordinator(DataUpdateCoordinator[GPMStatus]):
    """Check one custom component folder against one GitHub repository."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        interval = CHECK_INTERVALS[self._interval_key(entry)]
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data[CONF_FOLDER]}",
            update_interval=interval,
            config_entry=entry,
        )
        self.entry = entry
        self.folder: str = entry.data[CONF_FOLDER]
        owner, repo = split_slug(entry.data[CONF_REPO])
        self.owner = owner
        self.repo_name = repo
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._persisted: dict = {}
        self._io = asyncio.Lock()
        self.installing = False

    @property
    def repo(self) -> str:
        """Return the owner/repo slug."""

        return self.entry.data[CONF_REPO]

    @property
    def branch(self) -> str:
        """Return the configured branch."""

        return normalize_branch(self.entry.data.get(CONF_BRANCH))

    @property
    def update_mode(self) -> str:
        """Return manual or automatic."""

        return self._preferred(CONF_UPDATE_MODE)

    @property
    def check_interval(self) -> str:
        """Return the configured check interval key."""

        return self._interval_key(self.entry)

    async def async_load(self) -> None:
        """Load the last installed commit from disk."""

        self._persisted = await self._store.async_load() or {}

    async def async_install(self, *, force: bool = False) -> None:
        """Download the checked commit and replace the custom component folder."""

        async with self._io:
            await self._install_locked(force=force)

    async def _install_locked(self, *, force: bool) -> None:
        """Install while the coordinator I/O lock is held."""

        if self.installing:
            return
        self.installing = True
        self.async_update_listeners()
        try:
            status = self.data
            if status is None or force:
                status = await self._fetch_status(apply_policy=False)
            if (
                not force
                and status.installed_sha
                and status.installed_sha == status.remote_sha
            ):
                return
            version = await self._apply(status.remote_sha)
            installed, latest = in_sync_displays(version)
            self._persisted = persisted_state(
                bootstrapped=True, installed_sha=status.remote_sha
            )
            await self._store.async_save(self._persisted)
            self._notify_restart()
            self.async_set_updated_data(
                GPMStatus(
                    installed_sha=status.remote_sha,
                    remote_sha=status.remote_sha,
                    installed_display=installed,
                    latest_display=latest,
                    commit_message=status.commit_message,
                    update_available=False,
                    local_version=version,
                    remote_version=version,
                )
            )
            _LOGGER.info(
                "Installed %s %s from %s@%s",
                self.folder,
                version,
                self.repo,
                status.remote_sha[:7],
            )
        finally:
            self.installing = False
            self.async_update_listeners()

    def attributes(self) -> dict[str, str | None]:
        """Return token-free attributes for the update entity."""

        status = self.data
        return status_attributes(
            folder=self.folder,
            repo=self.repo,
            branch=self.branch,
            installed_sha=status.installed_sha if status else None,
            remote_sha=status.remote_sha if status else None,
        )

    async def _async_update_data(self) -> GPMStatus:
        async with self._io:
            try:
                return await self._fetch_status(apply_policy=True)
            except InvalidAuth as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except GPMError as err:
                raise UpdateFailed(str(err)) from err

    async def _fetch_status(self, *, apply_policy: bool) -> GPMStatus:
        local_version = await self.hass.async_add_executor_job(
            read_local_version, Path(self.hass.config.config_dir), self.folder
        )
        evaluation = await evaluate_update(
            self._client(),
            owner=self.owner,
            repo=self.repo_name,
            branch=self.branch,
            folder=self.folder,
            local_version=local_version,
            bootstrapped=bool(self._persisted.get("bootstrapped")),
            installed_sha=self._persisted.get("installed_sha"),
            update_mode=self.update_mode,
        )
        if not apply_policy:
            return self._status_from(evaluation, installed_sha=evaluation.decision.installed_sha)

        self._persisted = persisted_state(
            bootstrapped=True,
            installed_sha=evaluation.decision.installed_sha,
        )
        await self._store.async_save(self._persisted)

        if evaluation.decision.should_install:
            _LOGGER.info(
                "Automatically installing %s from %s (%s)",
                self.folder,
                self.repo,
                evaluation.remote_sha[:7],
            )
            self.installing = True
            self.async_update_listeners()
            try:
                version = await self._apply(evaluation.remote_sha)
            finally:
                self.installing = False
                self.async_update_listeners()
            self._persisted = persisted_state(
                bootstrapped=True, installed_sha=evaluation.remote_sha
            )
            await self._store.async_save(self._persisted)
            self._notify_restart()
            installed, latest = in_sync_displays(version)
            return GPMStatus(
                installed_sha=evaluation.remote_sha,
                remote_sha=evaluation.remote_sha,
                installed_display=installed,
                latest_display=latest,
                commit_message=evaluation.commit_message,
                update_available=False,
                local_version=version,
                remote_version=version,
            )

        if evaluation.update_available:
            _LOGGER.info(
                "Update available for %s: %s -> %s",
                self.folder,
                evaluation.installed_display,
                evaluation.latest_display,
            )
        return self._status_from(evaluation, installed_sha=evaluation.decision.installed_sha)

    def _status_from(self, evaluation: Evaluation, *, installed_sha: str | None) -> GPMStatus:
        return GPMStatus(
            installed_sha=installed_sha,
            remote_sha=evaluation.remote_sha,
            installed_display=evaluation.installed_display,
            latest_display=evaluation.latest_display,
            commit_message=evaluation.commit_message,
            update_available=evaluation.update_available,
            local_version=evaluation.local_version,
            remote_version=evaluation.remote_version,
        )

    async def _apply(self, sha: str) -> str:
        def _prepare() -> Path:
            return Path(tempfile.mkdtemp(prefix="gpm-download-"))

        temp_dir = await self.hass.async_add_executor_job(_prepare)
        zip_path = temp_dir / "repo.zip"
        try:
            await self._client().download_archive(self.owner, self.repo_name, sha, zip_path)
            return await self.hass.async_add_executor_job(
                install_archive,
                zip_path,
                Path(self.hass.config.config_dir),
                self.folder,
            )
        finally:
            await self.hass.async_add_executor_job(_remove_tree, temp_dir)

    def _client(self) -> GitHubClient:
        return GitHubClient(
            async_get_clientsession(self.hass),
            self.entry.data.get(CONF_TOKEN) or "",
        )

    def _notify_restart(self) -> None:
        issue_id = ISSUE_RESTART.format(entry_id=self.entry.entry_id)
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="restart_required",
            translation_placeholders={"name": self.folder},
        )
        if self.hass.services.has_service("persistent_notification", "create"):
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "GPM restart required",
                        "message": (
                            f"GPM updated `{self.folder}`. Restart Home Assistant to load the new code."
                        ),
                        "notification_id": NOTIFICATION_RESTART.format(
                            entry_id=self.entry.entry_id
                        ),
                    },
                )
            )

    def clear_restart_notice(self) -> None:
        """Drop the restart issue. Called on startup, after a restart has happened."""

        ir.async_delete_issue(
            self.hass, DOMAIN, ISSUE_RESTART.format(entry_id=self.entry.entry_id)
        )
        if self.hass.services.has_service("persistent_notification", "dismiss"):
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {
                        "notification_id": NOTIFICATION_RESTART.format(
                            entry_id=self.entry.entry_id
                        )
                    },
                )
            )

    def _preferred(self, key: str) -> str:
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data[key]

    @staticmethod
    def _interval_key(entry: ConfigEntry) -> str:
        if CONF_CHECK_INTERVAL in entry.options:
            return entry.options[CONF_CHECK_INTERVAL]
        return entry.data[CONF_CHECK_INTERVAL]


def _remove_tree(path: Path) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)
