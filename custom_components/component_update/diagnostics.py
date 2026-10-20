"""Diagnostics with the GitHub token removed."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CHECK_INTERVAL, CONF_UPDATE_MODE, DOMAIN
from .coordinator import ComponentUpdateCoordinator
from .repo import redact_config


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for one Component Update entry."""

    coordinator: ComponentUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    status = coordinator.data
    return {
        "config": redact_config(dict(entry.data)),
        "options": {
            CONF_UPDATE_MODE: coordinator.update_mode,
            CONF_CHECK_INTERVAL: coordinator.check_interval,
        },
        "installing": coordinator.installing,
        "status": None
        if status is None
        else {
            "installed_version": status.installed_display,
            "latest_version": status.latest_display,
            "installed_commit": status.installed_sha,
            "latest_commit": status.remote_sha,
            "update_available": status.update_available,
            "local_version": status.local_version,
            "remote_version": status.remote_version,
        },
        "last_error": str(coordinator.last_exception) if coordinator.last_exception else None,
    }
