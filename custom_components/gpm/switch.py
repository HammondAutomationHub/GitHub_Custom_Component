"""Switch that pauses or resumes updates for one folder."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GPMCoordinator
from .entity import GPMEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the pause switch."""

    coordinator: GPMCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GPMPauseSwitch(coordinator)])


class GPMPauseSwitch(GPMEntity, SwitchEntity):
    """On means this folder stays on the installed revision."""

    _attr_translation_key = "pause"

    def __init__(self, coordinator: GPMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pause"

    @property
    def is_on(self) -> bool:
        return self.coordinator.paused

    async def async_turn_on(self, **kwargs: object) -> None:
        """Pause updates without changing the installed files."""

        await self.coordinator.async_set_paused(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Allow the next check to follow the branch again."""

        await self.coordinator.async_set_paused(False)
