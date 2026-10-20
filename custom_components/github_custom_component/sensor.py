"""Status text for the last GitHub check."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GitHubCustomComponentCoordinator
from .entity import GitHubCustomComponentEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the status sensor."""

    coordinator: GitHubCustomComponentCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GitHubCustomComponentStatusSensor(coordinator)])


class GitHubCustomComponentStatusSensor(GitHubCustomComponentEntity, SensorEntity):
    """Show whether the folder is current, paused, or the check failed."""

    _attr_translation_key = "status"

    def __init__(self, coordinator: GitHubCustomComponentCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_status"

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return self.coordinator.status_text()
