"""Shared entity helpers."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GitHubCustomComponentCoordinator


class GitHubCustomComponentEntity(CoordinatorEntity[GitHubCustomComponentCoordinator]):
    """Base entity for one configured integration folder."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GitHubCustomComponentCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=f"GitHub - Custom_Component {coordinator.folder}",
            manufacturer="Hammond Automation Hub",
            model="Custom integration updater",
            configuration_url=f"https://github.com/{coordinator.repo}",
        )
