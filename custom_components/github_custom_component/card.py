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

CARD_FILENAME = "github-custom-component-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"
LOCAL_URL = f"/local/{DOMAIN}/{CARD_FILENAME}"
_REGISTERED = f"{DOMAIN}_card_registered"


def _publish_card(source: Path, www_dir: Path) -> str:
    """Copy the card into config/www and return a cache-busted /local URL."""

    www_dir.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    destination = www_dir / CARD_FILENAME
    if not destination.is_file() or destination.read_bytes() != data:
        destination.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()[:12]
    return f"{LOCAL_URL}?v={digest}"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it when a dashboard opens."""

    if hass.data.get(_REGISTERED):
        return
    source = Path(__file__).parent / "www" / CARD_FILENAME
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(source), False)]
        )
    except Exception:
        _LOGGER.exception("Could not publish the dashboard card at %s", CARD_URL)
    try:
        url = await hass.async_add_executor_job(
            _publish_card, source, Path(hass.config.path("www", DOMAIN))
        )
    except Exception:
        _LOGGER.exception("Could not copy the dashboard card into config/www")
        url = CARD_URL
    try:
        add_extra_js_url(hass, url)
    except Exception:
        _LOGGER.exception("Could not attach the dashboard card to the frontend")
    try:
        stored = await _register_lovelace_resource(hass, url)
    except Exception:
        _LOGGER.exception("Could not store the dashboard card resource")
        stored = False
    if stored:
        _LOGGER.info("Dashboard card registered at %s", url)
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

    base = LOCAL_URL
    existing = next(
        (
            item
            for item in collection.async_items()
            if str(item.get("url", "")).split("?", 1)[0] in {base, CARD_URL}
        ),
        None,
    )
    if existing is None:
        await collection.async_create_item({"res_type": "module", "url": url})
        return True
    if existing.get("url") != url:
        await collection.async_update_item(existing["id"], {"url": url})
    return True
