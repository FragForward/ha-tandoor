"""WebSocket API for the Tandoor integration.

Used by the bundled Lovelace card to load a recipe (image, times, ingredients,
steps, rating) for the in-page popup and to write the rating back — this works
inside Fully Kiosk where opening the recipe in a new tab is blocked.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .api import EssensplanError, TandoorError
from .const import DOMAIN
from .coordinator import TandoorConfigEntry


@callback
def _entry_for_entity(
    hass: HomeAssistant, entity_id: str
) -> TandoorConfigEntry | None:
    """Resolve the Tandoor config entry that owns a given sensor entity."""
    entity = er.async_get(hass).async_get(entity_id)
    if entity is None or entity.config_entry_id is None:
        return None
    entry = hass.config_entries.async_get_entry(entity.config_entry_id)
    if entry is None or entry.domain != DOMAIN:
        return None
    return entry


@callback
def _resolve_entry(
    hass: HomeAssistant, entity_id: str | None
) -> TandoorConfigEntry | None:
    """Pick the config entry for the request.

    Prefer the entry that owns the card's sensor; fall back to the only loaded
    Tandoor entry when the card did not send an entity_id (single instance).
    """
    if entity_id:
        entry = _entry_for_entity(hass, entity_id)
        if entry is not None and getattr(entry, "runtime_data", None) is not None:
            return entry
    loaded = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if getattr(entry, "runtime_data", None) is not None
    ]
    return loaded[0] if len(loaded) == 1 else None


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tandoor/recipe",
        vol.Required("recipe_id"): int,
        vol.Optional("entity_id"): str,
    }
)
@websocket_api.async_response
async def ws_recipe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return a trimmed recipe detail for the card popup."""
    entry = _resolve_entry(hass, msg.get("entity_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Tandoor instance not found")
        return
    try:
        recipe = await entry.runtime_data.client.get_recipe(msg["recipe_id"])
    except TandoorError as err:
        connection.send_error(msg["id"], "tandoor_error", str(err))
        return
    connection.send_result(msg["id"], recipe)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tandoor/set_rating",
        vol.Required("recipe_id"): int,
        vol.Required("rating"): vol.Any(None, vol.All(int, vol.Range(min=0, max=5))),
        vol.Optional("entity_id"): str,
    }
)
@websocket_api.async_response
async def ws_set_rating(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Set the recipe rating (via the user's cook log) and refresh the plan."""
    entry = _resolve_entry(hass, msg.get("entity_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Tandoor instance not found")
        return
    try:
        await entry.runtime_data.client.set_rating(msg["recipe_id"], msg["rating"])
        await entry.runtime_data.mealplan.async_request_refresh()
    except TandoorError as err:
        connection.send_error(msg["id"], "tandoor_error", str(err))
        return
    connection.send_result(msg["id"], {"rating": msg["rating"]})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tandoor/kochliste_zutaten",
        vol.Required("kid"): str,
        vol.Optional("entity_id"): str,
    }
)
@websocket_api.async_response
async def ws_kochliste_zutaten(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the shopping state of one Kochliste recipe's ingredients.

    Groups: 'kaufen' (to buy, with 'abgehakt'/'gesendet' flags) and 'daheim'
    (always on hand). Data comes from the Essensplan website's einkauf API.
    """
    entry = _resolve_entry(hass, msg.get("entity_id"))
    if entry is None or entry.runtime_data.kochliste is None:
        connection.send_error(msg["id"], "not_found", "Kochliste not available")
        return
    kid = msg["kid"]
    try:
        data = await entry.runtime_data.kochliste.client.einkauf()
    except EssensplanError as err:
        connection.send_error(msg["id"], "essensplan_error", str(err))
        return
    abgehakt = {
        int(fid)
        for fid in (data.get("abgehakt") or {}).get(kid, [])
    }

    def _menge(zutat: dict[str, Any]) -> str:
        summen: dict[str, float] = {}
        for verwendung in zutat.get("verwendungen") or []:
            if verwendung.get("kid") != kid or not verwendung.get("amount"):
                continue
            unit = str(verwendung.get("unit") or "")
            summen[unit] = summen.get(unit, 0) + float(verwendung["amount"])
        return " + ".join(
            f"{round(menge, 2):g} {unit}".strip() for unit, menge in summen.items()
        )

    kaufen: list[dict[str, Any]] = []
    daheim: list[dict[str, Any]] = []
    for zutat in data.get("zutaten") or []:
        if not any(
            verwendung.get("kid") == kid
            for verwendung in zutat.get("verwendungen") or []
        ):
            continue
        eintrag = {"name": zutat.get("name"), "menge": _menge(zutat)}
        if zutat.get("onhand"):
            daheim.append(eintrag)
        else:
            eintrag["gesendet"] = bool(zutat.get("gesendet"))
            eintrag["abgehakt"] = int(zutat.get("food_id") or 0) in abgehakt
            kaufen.append(eintrag)
    connection.send_result(msg["id"], {"kaufen": kaufen, "daheim": daheim})


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the Tandoor WebSocket commands (idempotent per HA start)."""
    websocket_api.async_register_command(hass, ws_recipe)
    websocket_api.async_register_command(hass, ws_set_rating)
    websocket_api.async_register_command(hass, ws_kochliste_zutaten)
