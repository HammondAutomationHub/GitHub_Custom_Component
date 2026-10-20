"""Version dropdown for rolling a managed folder back."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ComponentUpdateCoordinator
from .entity import ComponentUpdateEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the version selector."""

    async_add_entities([ComponentUpdateVersionSelect(hass.data[DOMAIN][entry.entry_id])])


class ComponentUpdateVersionSelect(ComponentUpdateEntity, SelectEntity):
    """Pick a tag or recent commit. Installing it is a separate button."""

    _attr_translation_key = "version"

    def __init__(self, coordinator: ComponentUpdateCoordinator) -> None:
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

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Explain the result of installing the chosen version."""

        return {
            "effect": (
                "Installing the selected version pauses updates. "
                "The folder stays on that version until Updates paused is turned off "
                "or the latest version is installed."
            )
        }

    async def async_select_option(self, option: str) -> None:
        try:
            self.coordinator.select_version(option)
        except KeyError as err:
            raise HomeAssistantError(f"{option} is not an available version.") from err
