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

from .api import TandoorError
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


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the Tandoor WebSocket commands (idempotent per HA start)."""
    websocket_api.async_register_command(hass, ws_recipe)
    websocket_api.async_register_command(hass, ws_set_rating)
