"""Update entity for a custom integration tracked by GitHub - Custom_Component."""

from __future__ import annotations

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UPDATE_MODE_AUTOMATIC
from .coordinator import GitHubCustomComponentCoordinator
from .entity import GitHubCustomComponentEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the update entity for this folder."""

    async_add_entities([ComponentRepositoryUpdateEntity(hass.data[DOMAIN][entry.entry_id])])


class ComponentRepositoryUpdateEntity(GitHubCustomComponentEntity, UpdateEntity):
    """Show the installed and remote versions and install on request."""

    _attr_translation_key = "repository"
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.RELEASE_NOTES
    )

    def __init__(self, coordinator: GitHubCustomComponentCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_update"

    @property
    def installed_version(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.installed_display

    @property
    def latest_version(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.latest_display

    @property
    def release_url(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return (
            f"https://github.com/{self.coordinator.repo}/commit/"
            f"{self.coordinator.data.remote_sha}"
        )

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Use the coordinator decision so a new commit is shown even when the manifest version stays the same."""

        if self.coordinator.data is not None:
            return self.coordinator.data.update_available
        return super().version_is_newer(latest_version, installed_version)

    @property
    def release_summary(self) -> str | None:
        """Short result shown on the update card."""

        return self.coordinator.status_text()

    @property
    def title(self) -> str | None:
        """Show the pause on the update card after a rollback."""

        if self.coordinator.paused:
            return "Updates are paused on the installed version"
        return None

    @property
    def in_progress(self) -> bool:
        return self.coordinator.installing

    @property
    def auto_update(self) -> bool:
        return (
            self.coordinator.update_mode == UPDATE_MODE_AUTOMATIC
            and not self.coordinator.paused
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        return self.coordinator.attributes()

    def release_notes(self) -> str | None:
        if self.coordinator.data is None:
            return None
        message = self.coordinator.data.commit_message or None
        if not self.coordinator.paused:
            return message
        paused = (
            "Updates are paused on the installed version. "
            "Automatic checks will not replace it. "
            "Turn off Updates paused, or install the latest version, to follow the branch again."
        )
        if message:
            return f"{paused}\n\n{message}"
        return paused

    async def async_install(self, version: str | None, backup: bool, **kwargs: object) -> None:
        """Download the latest commit over the custom component folder."""

        await self.coordinator.async_install()
