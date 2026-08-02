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
