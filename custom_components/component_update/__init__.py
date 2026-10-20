"""Component Update keeps installed custom integrations current."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_FOLDER,
    CONF_VERSION,
    DOMAIN,
    SERVICE_CHECK,
    SERVICE_INSTALL,
    SERVICE_ROLLBACK,
)
from .coordinator import ComponentUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.UPDATE,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SWITCH,
]

CHECK_SCHEMA = vol.Schema({vol.Optional(CONF_FOLDER): cv.string})
INSTALL_SCHEMA = vol.Schema({vol.Required(CONF_FOLDER): cv.string})
ROLLBACK_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_FOLDER): cv.string,
        vol.Required(CONF_VERSION): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register services once."""

    hass.data.setdefault(DOMAIN, {})

    async def _coordinators(folder: str | None) -> list[ComponentUpdateCoordinator]:
        coordinators = list(hass.data[DOMAIN].values())
        if not folder:
            return coordinators
        return [item for item in coordinators if item.folder == folder]

    async def handle_check(call: ServiceCall) -> None:
        folder = call.data.get(CONF_FOLDER) or None
        for coordinator in await _coordinators(folder):
            await coordinator.async_request_refresh()

    async def handle_install(call: ServiceCall) -> None:
        folder = call.data[CONF_FOLDER]
        matches = await _coordinators(folder)
        if not matches:
            raise ServiceValidationError(f"No Component Update entry is configured for {folder}.")
        await matches[0].async_install()

    async def handle_rollback(call: ServiceCall) -> None:
        folder = call.data[CONF_FOLDER]
        matches = await _coordinators(folder)
        if not matches:
            raise ServiceValidationError(f"No Component Update entry is configured for {folder}.")
        await matches[0].async_install_ref(call.data[CONF_VERSION], paused=True)

    hass.services.async_register(DOMAIN, SERVICE_CHECK, handle_check, schema=CHECK_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_INSTALL, handle_install, schema=INSTALL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ROLLBACK, handle_rollback, schema=ROLLBACK_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one folder-to-repository mapping."""

    coordinator = ComponentUpdateCoordinator(hass, entry)
    await coordinator.async_load()
    coordinator.clear_restart_notice()
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Component Update entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
