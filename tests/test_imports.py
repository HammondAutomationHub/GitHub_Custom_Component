"""The integration package imports against the installed Home Assistant version."""

from __future__ import annotations


def test_integration_modules_import() -> None:
    import custom_components.component_update as component_update
    from custom_components.component_update import button, diagnostics, select, switch, update
    from custom_components.component_update.config_flow import ComponentUpdateConfigFlow, ComponentUpdateOptionsFlow
    from custom_components.component_update.const import DOMAIN

    assert DOMAIN == "component_update"
    assert component_update.PLATFORMS
    assert ComponentUpdateConfigFlow.async_get_options_flow
    assert ComponentUpdateOptionsFlow
    assert update.ComponentRepositoryUpdateEntity
    assert button.ComponentUpdateInstallVersionButton
    assert select.ComponentUpdateVersionSelect
    assert switch.ComponentUpdatePauseSwitch
    assert diagnostics.async_get_config_entry_diagnostics
