"""Buttons to check or reinstall a tracked integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Create check and reinstall buttons."""

    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ComponentUpdateCheckButton(coordinator),
            ComponentUpdateReinstallButton(coordinator),
            ComponentUpdateInstallVersionButton(coordinator),
        ]
    )


class ComponentUpdateCheckButton(ComponentUpdateEntity, ButtonEntity):
    """Check GitHub now. Available even when the last check failed."""

    _attr_translation_key = "check"

    def __init__(self, coordinator: ComponentUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_check"

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class ComponentUpdateReinstallButton(ComponentUpdateEntity, ButtonEntity):
    """Reinstall the current remote commit even when versions already match."""

    _attr_translation_key = "reinstall"

    def __init__(self, coordinator: ComponentUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_reinstall"

    @property
    def available(self) -> bool:
        return not self.coordinator.installing

    async def async_press(self) -> None:
        installed = (
            self.coordinator.data.installed_sha if self.coordinator.data is not None else None
        )
        if self.coordinator.paused and installed:
            await self.coordinator.async_install_ref(installed, paused=True)
            return
        await self.coordinator.async_install(force=True)


class ComponentUpdateInstallVersionButton(ComponentUpdateEntity, ButtonEntity):
    """Install the tag or commit chosen in the version dropdown."""

    _attr_translation_key = "install_version"

    def __init__(self, coordinator: ComponentUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_install_version"

    @property
    def available(self) -> bool:
        return self.coordinator.selected_ref is not None and not self.coordinator.installing

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """State the pause that follows this button."""

        return {
            "effect": (
                "Installs the rollback version and pauses updates on that revision."
            )
        }

    async def async_press(self) -> None:
        ref = self.coordinator.selected_ref
        if not ref:
            raise HomeAssistantError("Choose a version to roll back before installing it.")
        await self.coordinator.async_install_ref(ref, paused=True)
