"""Data update coordinators for the Tandoor integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    MealPlanEntry,
    ShoppingEntry,
    TandoorAuthenticationError,
    TandoorClient,
    TandoorConnectionError,
)
from .const import DOMAIN, MEALPLAN_DAYS, MEALPLAN_UPDATE_INTERVAL, SHOPPING_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

@dataclass
class TandoorData:
    """Runtime data for a Tandoor config entry."""

    client: TandoorClient
    shopping: TandoorShoppingCoordinator
    mealplan: TandoorMealplanCoordinator


TandoorConfigEntry = ConfigEntry[TandoorData]


class TandoorShoppingCoordinator(DataUpdateCoordinator[list[ShoppingEntry]]):
    """Polls the Tandoor shopping list."""

    config_entry: TandoorConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: TandoorConfigEntry, client: TandoorClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_shopping",
            update_interval=SHOPPING_UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> list[ShoppingEntry]:
        try:
            return await self.client.get_shopping_entries()
        except (TandoorAuthenticationError, TandoorConnectionError) as err:
            raise UpdateFailed(f"Error fetching shopping list: {err}") from err


class TandoorMealplanCoordinator(DataUpdateCoordinator[list[MealPlanEntry]]):
    """Polls the Tandoor meal plan for the next days."""

    config_entry: TandoorConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: TandoorConfigEntry, client: TandoorClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_mealplan",
            update_interval=MEALPLAN_UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> list[MealPlanEntry]:
        today = dt_util.now().date()
        try:
            return await self.client.get_meal_plans(
                today, today + timedelta(days=MEALPLAN_DAYS - 1)
            )
        except (TandoorAuthenticationError, TandoorConnectionError) as err:
            raise UpdateFailed(f"Error fetching meal plan: {err}") from err
