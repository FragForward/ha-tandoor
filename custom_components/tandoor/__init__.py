"""The Tandoor Recipes integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TandoorClient
from .const import DOMAIN, FRONTEND_URL, FRONTEND_VERSION
from .coordinator import (
    TandoorConfigEntry,
    TandoorData,
    TandoorMealplanCoordinator,
    TandoorShoppingCoordinator,
)

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR, Platform.TODO]


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and load it in the frontend."""
    if hass.data.get(f"{DOMAIN}_frontend_registered"):
        return
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                FRONTEND_URL,
                str(Path(__file__).parent / "frontend" / "tandoor-mealplan-card.js"),
                cache_headers=False,
            )
        ]
    )
    add_extra_js_url(hass, f"{FRONTEND_URL}?v={FRONTEND_VERSION}")
    hass.data[f"{DOMAIN}_frontend_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: TandoorConfigEntry) -> bool:
    """Set up Tandoor from a config entry."""
    await _async_register_frontend(hass)

    client = TandoorClient(
        base_url=entry.data[CONF_URL],
        api_token=entry.data[CONF_API_TOKEN],
        session=async_get_clientsession(
            hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True)
        ),
    )

    shopping = TandoorShoppingCoordinator(hass, entry, client)
    mealplan = TandoorMealplanCoordinator(hass, entry, client)
    await shopping.async_config_entry_first_refresh()
    await mealplan.async_config_entry_first_refresh()

    entry.runtime_data = TandoorData(
        client=client, shopping=shopping, mealplan=mealplan
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TandoorConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
