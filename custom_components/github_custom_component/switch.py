"""Switch that pauses or resumes updates for one folder."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Create the pause switch."""

    coordinator: GitHubCustomComponentCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GitHubCustomComponentPauseSwitch(coordinator)])


class GitHubCustomComponentPauseSwitch(GitHubCustomComponentEntity, SwitchEntity):
    """On means this folder stays on the installed revision."""

    _attr_translation_key = "pause"

    def __init__(self, coordinator: GitHubCustomComponentCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_pause"

    @property
    def is_on(self) -> bool:
        return self.coordinator.paused

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Say what the switch is doing right now."""

        if self.coordinator.paused:
            effect = (
                "Updates are paused. This folder stays on the installed version."
            )
        else:
            effect = "Updates are not paused. Checks can follow the branch."
        return {"effect": effect}

    async def async_turn_on(self, **kwargs: object) -> None:
        """Pause updates without changing the installed files."""

        await self.coordinator.async_set_paused(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Allow the next check to follow the branch again."""

        await self.coordinator.async_set_paused(False)
