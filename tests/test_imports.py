"""The integration package imports against the installed Home Assistant version."""

from __future__ import annotations


def test_integration_modules_import() -> None:
    import custom_components.github_custom_component as github_custom_component
    from custom_components.github_custom_component import button, diagnostics, select, sensor, switch, update
    from custom_components.github_custom_component.config_flow import GitHubCustomComponentConfigFlow, GitHubCustomComponentOptionsFlow
    from custom_components.github_custom_component.const import DOMAIN

    assert DOMAIN == "github_custom_component"
    assert github_custom_component.PLATFORMS
    assert GitHubCustomComponentConfigFlow.async_get_options_flow
    assert GitHubCustomComponentOptionsFlow
    assert update.ComponentRepositoryUpdateEntity
    assert button.GitHubCustomComponentInstallVersionButton
    assert select.GitHubCustomComponentVersionSelect
    assert switch.GitHubCustomComponentPauseSwitch
    assert sensor.GitHubCustomComponentStatusSensor
    assert diagnostics.async_get_config_entry_diagnostics
