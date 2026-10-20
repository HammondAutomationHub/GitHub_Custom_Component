"""UI configuration for GPM."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CHECK_INTERVALS,
    CONF_BRANCH,
    CONF_CHECK_INTERVAL,
    CONF_FOLDER,
    CONF_REPO,
    CONF_TOKEN,
    CONF_UPDATE_MODE,
    DEFAULT_BRANCH,
    DOMAIN,
    INTERVAL_DAILY,
    UPDATE_MODE_MANUAL,
    UPDATE_MODES,
)
from .errors import GPMError, InvalidSchedule
from .installer import list_integrations
from .repo import schedule_error
from .validate import validate_repository


class GPMConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure one custom integration folder and the GitHub repo that updates it."""

    VERSION = 1

    def __init__(self) -> None:
        self._folder: str | None = None
        self._repo: str | None = None
        self._branch: str | None = None
        self._token: str = ""
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose an integration folder that is already installed."""

        if user_input is not None:
            self._folder = user_input[CONF_FOLDER]
            await self.async_set_unique_id(self._folder)
            self._abort_if_unique_id_configured()
            return await self.async_step_repo()

        folders = await self.hass.async_add_executor_job(
            list_integrations, Path(self.hass.config.config_dir)
        )
        if not folders:
            return self.async_abort(reason="no_integrations")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_FOLDER): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=folder, label=label)
                                for folder, label in folders
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_repo(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the GitHub repository, branch, and token."""

        errors: dict[str, str] = {}
        defaults = user_input or {}
        if user_input is not None:
            try:
                slug, branch = await validate_repository(
                    async_get_clientsession(self.hass),
                    user_input.get(CONF_TOKEN, ""),
                    user_input[CONF_REPO],
                    user_input.get(CONF_BRANCH) or DEFAULT_BRANCH,
                    self._folder or "",
                )
            except GPMError as err:
                errors["base"] = err.code
            else:
                self._repo = slug
                self._branch = branch
                self._token = user_input.get(CONF_TOKEN, "") or ""
                return await self.async_step_schedule()

        return self.async_show_form(
            step_id="repo",
            data_schema=self._repo_schema(defaults),
            errors=errors,
            description_placeholders={"folder": self._folder or ""},
        )

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose manual or automatic updates and how often to check."""

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                schedule_error(user_input[CONF_UPDATE_MODE], user_input[CONF_CHECK_INTERVAL])
            except InvalidSchedule:
                errors["base"] = "automatic_needs_interval"
            else:
                return self.async_create_entry(
                    title=self._folder or self._repo or DOMAIN,
                    data={
                        CONF_FOLDER: self._folder,
                        CONF_REPO: self._repo,
                        CONF_BRANCH: self._branch,
                        CONF_TOKEN: self._token,
                        CONF_UPDATE_MODE: user_input[CONF_UPDATE_MODE],
                        CONF_CHECK_INTERVAL: user_input[CONF_CHECK_INTERVAL],
                    },
                )

        return self.async_show_form(
            step_id="schedule",
            data_schema=self._schedule_schema(user_input),
            errors=errors,
            description_placeholders={"repo": self._repo or ""},
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start a token refresh when GitHub rejects the saved token."""

        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new token and verify it against the saved repository."""

        errors: dict[str, str] = {}
        entry = self._reauth_entry
        if entry is None:
            return self.async_abort(reason="unknown")
        if user_input is not None:
            try:
                await validate_repository(
                    async_get_clientsession(self.hass),
                    user_input[CONF_TOKEN],
                    entry.data[CONF_REPO],
                    entry.data.get(CONF_BRANCH),
                    entry.data[CONF_FOLDER],
                )
            except GPMError as err:
                errors["base"] = err.code
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_TOKEN: user_input[CONF_TOKEN]},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOKEN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
            description_placeholders={
                "repo": entry.data[CONF_REPO],
                "folder": entry.data[CONF_FOLDER],
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GPMOptionsFlow:
        """Return the options flow."""

        return GPMOptionsFlow()

    @staticmethod
    def _repo_schema(defaults: dict[str, Any]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_REPO, default=defaults.get(CONF_REPO, "")): TextSelector(),
                vol.Required(
                    CONF_BRANCH, default=defaults.get(CONF_BRANCH, DEFAULT_BRANCH)
                ): TextSelector(),
                vol.Optional(CONF_TOKEN, default=defaults.get(CONF_TOKEN, "")): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )

    @staticmethod
    def _schedule_schema(defaults: dict[str, Any] | None) -> vol.Schema:
        current = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_MODE,
                    default=current.get(CONF_UPDATE_MODE, UPDATE_MODE_MANUAL),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=UPDATE_MODES,
                        translation_key="update_mode",
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_CHECK_INTERVAL,
                    default=current.get(CONF_CHECK_INTERVAL, INTERVAL_DAILY),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=list(CHECK_INTERVALS),
                        translation_key="check_interval",
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )


class GPMOptionsFlow(OptionsFlow):
    """Change branch, token, and schedule for an existing entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and store updated options."""

        errors: dict[str, str] = {}
        entry = self.config_entry
        if user_input is not None:
            token = user_input.get(CONF_TOKEN) or entry.data.get(CONF_TOKEN, "")
            try:
                schedule_error(user_input[CONF_UPDATE_MODE], user_input[CONF_CHECK_INTERVAL])
                slug, branch = await validate_repository(
                    async_get_clientsession(self.hass),
                    token,
                    entry.data[CONF_REPO],
                    user_input[CONF_BRANCH],
                    entry.data[CONF_FOLDER],
                )
            except InvalidSchedule:
                errors["base"] = "automatic_needs_interval"
            except GPMError as err:
                errors["base"] = err.code
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_REPO: slug,
                        CONF_BRANCH: branch,
                        CONF_TOKEN: token,
                        CONF_UPDATE_MODE: user_input[CONF_UPDATE_MODE],
                        CONF_CHECK_INTERVAL: user_input[CONF_CHECK_INTERVAL],
                    },
                )
                return self.async_create_entry(
                    data={
                        CONF_UPDATE_MODE: user_input[CONF_UPDATE_MODE],
                        CONF_CHECK_INTERVAL: user_input[CONF_CHECK_INTERVAL],
                    }
                )

        mode = entry.options.get(CONF_UPDATE_MODE, entry.data.get(CONF_UPDATE_MODE))
        interval = entry.options.get(
            CONF_CHECK_INTERVAL, entry.data.get(CONF_CHECK_INTERVAL)
        )
        defaults = {
            CONF_BRANCH: entry.data.get(CONF_BRANCH, DEFAULT_BRANCH),
            CONF_UPDATE_MODE: mode,
            CONF_CHECK_INTERVAL: interval,
        }
        if user_input:
            defaults.update(user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BRANCH, default=defaults[CONF_BRANCH]): TextSelector(),
                    vol.Optional(CONF_TOKEN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                    vol.Required(
                        CONF_UPDATE_MODE, default=defaults[CONF_UPDATE_MODE]
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=UPDATE_MODES,
                            translation_key="update_mode",
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_CHECK_INTERVAL, default=defaults[CONF_CHECK_INTERVAL]
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=list(CHECK_INTERVALS),
                            translation_key="check_interval",
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "folder": entry.data[CONF_FOLDER],
                "repo": entry.data[CONF_REPO],
            },
        )
