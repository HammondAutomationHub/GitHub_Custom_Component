"""The integration package imports against the installed Home Assistant version."""

from __future__ import annotations


def test_integration_modules_import() -> None:
    import custom_components.github_custom_component as github_custom_component
    from custom_components.github_custom_component import button, card, diagnostics, select, sensor, switch, update
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
    assert sensor.GitHubCustomComponentInstalledVersionSensor
    assert sensor.GitHubCustomComponentDeployVersionSensor
    assert diagnostics.async_get_config_entry_diagnostics
    assert card.CARD_URL.endswith("github-custom-component-card.js")
    script = (
        __import__("pathlib").Path(__file__).parents[1]
        / "custom_components"
        / "github_custom_component"
        / "www"
        / "github-custom-component-card.js"
    ).read_text(encoding="utf-8")
    for key in ("repository", "check", "version", "install_version", "reinstall", "pause", "status"):
        assert key in script
