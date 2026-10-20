"""Buttons to check or reinstall a tracked integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Create check and reinstall buttons."""

    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            GPMCheckButton(coordinator),
            GPMReinstallButton(coordinator),
        ]
    )


class GPMCheckButton(GPMEntity, ButtonEntity):
    """Check GitHub now. Available even when the last check failed."""

    _attr_translation_key = "check"

    def __init__(self, coordinator: GPMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_check"

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class GPMReinstallButton(GPMEntity, ButtonEntity):
    """Reinstall the current remote commit even when versions already match."""

    _attr_translation_key = "reinstall"

    def __init__(self, coordinator: GPMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_reinstall"

    @property
    def available(self) -> bool:
        return not self.coordinator.installing

    async def async_press(self) -> None:
        await self.coordinator.async_install(force=True)
