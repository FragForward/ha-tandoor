"""The Tandoor Recipes integration."""

from __future__ import annotations

from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TandoorClient
from .coordinator import (
    TandoorConfigEntry,
    TandoorData,
    TandoorMealplanCoordinator,
    TandoorShoppingCoordinator,
)

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR, Platform.TODO]


async def async_setup_entry(hass: HomeAssistant, entry: TandoorConfigEntry) -> bool:
    """Set up Tandoor from a config entry."""
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
