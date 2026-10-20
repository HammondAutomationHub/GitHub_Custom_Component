"""The integration package imports against the installed Home Assistant version."""

from __future__ import annotations


def test_integration_modules_import() -> None:
    import custom_components.gpm as gpm
    from custom_components.gpm import button, diagnostics, update
    from custom_components.gpm.config_flow import GPMConfigFlow, GPMOptionsFlow
    from custom_components.gpm.const import DOMAIN

    assert DOMAIN == "gpm"
    assert gpm.PLATFORMS
    assert GPMConfigFlow.async_get_options_flow
    assert GPMOptionsFlow
    assert update.GPMUpdateEntity
    assert button.GPMCheckButton
    assert diagnostics.async_get_config_entry_diagnostics
