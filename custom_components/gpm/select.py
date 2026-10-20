"""Version dropdown for rolling a managed folder back."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GPMCoordinator
from .entity import GPMEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the version selector."""

    async_add_entities([GPMVersionSelect(hass.data[DOMAIN][entry.entry_id])])


class GPMVersionSelect(GPMEntity, SelectEntity):
    """Pick a tag or recent commit. Installing it is a separate button."""

    _attr_translation_key = "version"

    def __init__(self, coordinator: GPMCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_version"

    @property
    def available(self) -> bool:
        return not self.coordinator.installing

    @property
    def options(self) -> list[str]:
        return self.coordinator.version_labels

    @property
    def current_option(self) -> str:
        return self.coordinator.selected_version_label

    async def async_select_option(self, option: str) -> None:
        try:
            self.coordinator.select_version(option)
        except KeyError as err:
            raise HomeAssistantError(f"{option} is not an available version.") from err
