"""Services for the Tandoor integration (Kochliste actions).

The Kochliste services talk to the Essensplan website API (essensplan_url
option), not to Tandoor itself. They are registered once per Home Assistant
start and resolve the config entry dynamically, so they give a clean error
when the Kochliste feature is disabled or not (yet) configured.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .api import EssensplanError
from .const import DOMAIN
from .coordinator import TandoorConfigEntry

SERVICE_KOCHLISTE_GEKOCHT = "kochliste_gekocht"
SERVICE_KOCHLISTE_KOCHBAR = "kochliste_kochbar"
SERVICE_KOCHLISTE_BEWERTEN = "kochliste_bewerten"
SERVICE_KOCHLISTE_BRING = "kochliste_bring"
SERVICE_KOCHLISTE_WUNSCH = "kochliste_wunsch"
SERVICE_KOCHLISTE_NACHSCHUB = "kochliste_nachschub"

KOCHLISTE_WUNSCH_SCHEMA = vol.Schema({vol.Required("text"): cv.string})
SERVICE_KOCHLISTE_ADD = "kochliste_add"
SERVICE_KOCHLISTE_DEL = "kochliste_del"
SERVICE_KOCHLISTE_ZURUECK = "kochliste_zurueck"
SERVICE_KOCHLISTE_WUNSCH_DEL = "kochliste_wunsch_del"
SERVICE_KOCHLISTE_VORLAGE_ADD = "kochliste_vorlage_add"
SERVICE_KOCHLISTE_VORLAGE_DEL = "kochliste_vorlage_del"
KOCHLISTE_ADD_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("recipe_id"): vol.Coerce(int),
            vol.Optional("freitext"): cv.string,
        }
    ),
    cv.has_at_least_one_key("recipe_id", "freitext"),
)

KOCHLISTE_ID_SCHEMA = vol.Schema({vol.Required("id"): cv.string})
KOCHLISTE_BEWERTEN_SCHEMA = vol.Schema(
    {
        vol.Required("recipe_id"): vol.Coerce(int),
        vol.Required("sterne"): vol.All(vol.Coerce(int), vol.Range(min=0, max=5)),
        vol.Optional("kommentar", default=""): cv.string,
    }
)


@callback
def _kochliste_entry(hass: HomeAssistant) -> TandoorConfigEntry:
    """Return the loaded config entry that has the Kochliste enabled."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        data = getattr(entry, "runtime_data", None)
        if data is not None and data.kochliste is not None:
            return entry
    raise HomeAssistantError(
        "Kochliste is not available — check the essensplan_url option of the "
        "Tandoor integration"
    )


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register the Kochliste services (idempotent per Home Assistant start)."""
    if hass.services.has_service(DOMAIN, SERVICE_KOCHLISTE_GEKOCHT):
        return

    async def _refresh(entry: TandoorConfigEntry) -> None:
        await entry.runtime_data.kochliste.async_request_refresh()

    async def handle_gekocht(call: ServiceCall) -> None:
        """Mark a Kochliste item as cooked."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.kochliste_gekocht(
                call.data["id"]
            )
        except EssensplanError as err:
            raise HomeAssistantError(f"Kochliste gekocht failed: {err}") from err
        await _refresh(entry)

    async def handle_kochbar(call: ServiceCall) -> None:
        """Move a Kochliste item from 'einkaufen' to 'kochbar'."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.kochliste_kochbar(
                call.data["id"]
            )
        except EssensplanError as err:
            raise HomeAssistantError(f"Kochliste kochbar failed: {err}") from err
        await _refresh(entry)

    async def handle_bring(call: ServiceCall) -> None:
        """Send one recipe's shopping items to the shopping list (Bring)."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.rezept_bring(
                call.data["id"]
            )
        except EssensplanError as err:
            raise HomeAssistantError(f"Kochliste bring failed: {err}") from err
        await _refresh(entry)

    async def handle_add(call: ServiceCall) -> None:
        """Add a dish to the Kochliste (recipe id or free text)."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.kochliste_add(
                recipe_id=call.data.get("recipe_id"),
                freitext=call.data.get("freitext"),
            )
        except EssensplanError as err:
            raise HomeAssistantError(f"Kochliste add failed: {err}") from err
        await _refresh(entry)

    async def handle_del(call: ServiceCall) -> None:
        """Remove a Kochliste item (not counted as cooked)."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.kochliste_del(call.data["id"])
        except EssensplanError as err:
            raise HomeAssistantError(f"Kochliste del failed: {err}") from err
        await _refresh(entry)

    async def handle_zurueck(call: ServiceCall) -> None:
        """Move a Kochliste item back to shopping state."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.einkauf_zurueck(call.data["id"])
        except EssensplanError as err:
            raise HomeAssistantError(f"Kochliste zurueck failed: {err}") from err
        await _refresh(entry)

    async def handle_wunsch(call: ServiceCall) -> None:
        """Add a wish (text or link) for the next proposal round."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.wunsch(call.data["text"])
        except EssensplanError as err:
            raise HomeAssistantError(f"Kochliste wunsch failed: {err}") from err

    async def handle_nachschub(call: ServiceCall) -> None:
        """Request a new proposal round on the next watchdog run."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.nachschub_anfordern()
        except EssensplanError as err:
            raise HomeAssistantError(f"Kochliste nachschub failed: {err}") from err

    async def handle_wunsch_del(call: ServiceCall) -> None:
        """Remove a wish from the wish basket."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.wunsch_del(call.data["id"])
        except EssensplanError as err:
            raise HomeAssistantError(f"Wunsch del failed: {err}") from err

    async def handle_vorlage_add(call: ServiceCall) -> None:
        """Add a reusable wish template."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.wunsch_vorlage_add(
                call.data["text"]
            )
        except EssensplanError as err:
            raise HomeAssistantError(f"Vorlage add failed: {err}") from err

    async def handle_vorlage_del(call: ServiceCall) -> None:
        """Remove a reusable wish template."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.wunsch_vorlage_del(
                call.data["text"]
            )
        except EssensplanError as err:
            raise HomeAssistantError(f"Vorlage del failed: {err}") from err

    async def handle_bewerten(call: ServiceCall) -> None:
        """Rate a recipe 0-5 stars with an optional comment."""
        entry = _kochliste_entry(hass)
        try:
            await entry.runtime_data.kochliste.client.rezept_stern(
                call.data["recipe_id"],
                call.data["sterne"],
                call.data.get("kommentar") or None,
            )
        except EssensplanError as err:
            raise HomeAssistantError(f"Kochliste bewerten failed: {err}") from err
        await _refresh(entry)
        # The rating also shows up in the Tandoor meal plan sensors.
        await entry.runtime_data.mealplan.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_KOCHLISTE_GEKOCHT, handle_gekocht, schema=KOCHLISTE_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_KOCHLISTE_KOCHBAR, handle_kochbar, schema=KOCHLISTE_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_KOCHLISTE_BEWERTEN,
        handle_bewerten,
        schema=KOCHLISTE_BEWERTEN_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_KOCHLISTE_BRING, handle_bring, schema=KOCHLISTE_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_KOCHLISTE_WUNSCH,
        handle_wunsch,
        schema=KOCHLISTE_WUNSCH_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_KOCHLISTE_NACHSCHUB, handle_nachschub, schema=vol.Schema({})
    )
    hass.services.async_register(
        DOMAIN, SERVICE_KOCHLISTE_ADD, handle_add, schema=KOCHLISTE_ADD_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_KOCHLISTE_DEL, handle_del, schema=KOCHLISTE_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_KOCHLISTE_ZURUECK, handle_zurueck, schema=KOCHLISTE_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_KOCHLISTE_WUNSCH_DEL,
        handle_wunsch_del,
        schema=KOCHLISTE_ID_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_KOCHLISTE_VORLAGE_ADD,
        handle_vorlage_add,
        schema=KOCHLISTE_WUNSCH_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_KOCHLISTE_VORLAGE_DEL,
        handle_vorlage_del,
        schema=KOCHLISTE_WUNSCH_SCHEMA,
    )
