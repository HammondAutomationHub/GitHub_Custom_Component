"""Register the dashboard card that ships with the integration."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_URL = f"/{DOMAIN}/github-custom-component-card.js"
_REGISTERED = f"{DOMAIN}_card_registered"


def _versioned_url(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return f"{CARD_URL}?v={digest}"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it when a dashboard opens."""

    if hass.data.get(_REGISTERED):
        return
    path = Path(__file__).parent / "www" / "github-custom-component-card.js"
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(path), False)])
    url = await hass.async_add_executor_job(_versioned_url, path)
    if not await _register_lovelace_resource(hass, url):
        add_extra_js_url(hass, url)
    hass.data[_REGISTERED] = True


async def _register_lovelace_resource(hass: HomeAssistant, url: str) -> bool:
    """Store the card as a dashboard resource so the picker can see it."""

    lovelace = hass.data.get(LOVELACE_DOMAIN)
    if not isinstance(lovelace, dict):
        return False
    collection = lovelace.get("resources")
    if not isinstance(collection, ResourceStorageCollection):
        return False
    if not collection.loaded:
        await collection.async_load()
        collection.loaded = True

    base = CARD_URL
    existing = next(
        (
            item
            for item in collection.async_items()
            if str(item.get("url", "")).split("?", 1)[0] == base
        ),
        None,
    )
    if existing is None:
        await collection.async_create_item({"res_type": "module", "url": url})
        _LOGGER.debug("Registered dashboard card resource %s", url)
        return True
    if existing.get("url") != url:
        await collection.async_update_item(existing["id"], {"url": url})
        _LOGGER.debug("Updated dashboard card resource %s", url)
    return True
