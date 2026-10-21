"""Register the dashboard card that ships with the integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

CARD_URL = f"/{DOMAIN}/github-custom-component-card.js"
_REGISTERED = f"{DOMAIN}_card_registered"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it with the Home Assistant frontend."""

    if hass.data.get(_REGISTERED):
        return
    path = Path(__file__).parent / "www" / "github-custom-component-card.js"
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(path), False)])
    add_extra_js_url(hass, CARD_URL)
    hass.data[_REGISTERED] = True
