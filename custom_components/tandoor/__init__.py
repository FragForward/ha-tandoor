"""The Tandoor Recipes integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EssensplanClient, TandoorClient
from .bring_sync import TandoorBringSync
from .const import (
    CONF_BRING_ENTITY,
    CONF_ESSENSPLAN_URL,
    DEFAULT_ESSENSPLAN_URL,
    DOMAIN,
    FRONTEND_URL,
    FRONTEND_VERSION,
)
from .coordinator import (
    TandoorConfigEntry,
    TandoorData,
    TandoorKochlisteCoordinator,
    TandoorMealplanCoordinator,
    TandoorShoppingCoordinator,
)
from .services import async_register_services
from .websocket import async_register_websocket_api

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


def _register_websocket_api(hass: HomeAssistant) -> None:
    """Register the WebSocket commands once per Home Assistant start."""
    if hass.data.get(f"{DOMAIN}_ws_registered"):
        return
    async_register_websocket_api(hass)
    hass.data[f"{DOMAIN}_ws_registered"] = True


async def _async_update_listener(
    hass: HomeAssistant, entry: TandoorConfigEntry
) -> None:
    """Reload the entry when options (e.g. essensplan_url) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: TandoorConfigEntry) -> bool:
    """Set up Tandoor from a config entry."""
    await _async_register_frontend(hass)
    _register_websocket_api(hass)
    async_register_services(hass)

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

    # Optional Kochliste feature (Essensplan website, not Tandoor). An empty
    # URL disables it; an unreachable API must never fail the setup — the
    # coordinator just logs and keeps retrying.
    kochliste: TandoorKochlisteCoordinator | None = None
    essensplan_url = (
        entry.options.get(CONF_ESSENSPLAN_URL, DEFAULT_ESSENSPLAN_URL) or ""
    ).strip()
    if essensplan_url:
        essensplan = EssensplanClient(
            base_url=essensplan_url, session=async_get_clientsession(hass)
        )
        kochliste = TandoorKochlisteCoordinator(hass, entry, essensplan)
        await kochliste.async_refresh()

        # Optional Bring return channel: watch the Bring todo list and mark
        # recipes cookable once all their sent ingredients are checked off.
        bring_entity = (entry.options.get(CONF_BRING_ENTITY) or "").strip()
        if bring_entity:
            bring_sync = TandoorBringSync(hass, essensplan, bring_entity, kochliste)
            bring_sync.async_setup()
            entry.async_on_unload(bring_sync.async_teardown)

    entry.runtime_data = TandoorData(
        client=client, shopping=shopping, mealplan=mealplan, kochliste=kochliste
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TandoorConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
