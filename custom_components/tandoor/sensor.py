"""Sensor platform for the Tandoor integration."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import MealPlanEntry
from .const import MEALPLAN_DAYS
from .coordinator import (
    TandoorConfigEntry,
    TandoorMealplanCoordinator,
    TandoorShoppingCoordinator,
)
from .entity import TandoorEntity

PARALLEL_UPDATES = 0


def _meal_dict(plan: MealPlanEntry) -> dict[str, Any]:
    """Attribute representation of one meal."""
    return {
        "name": plan.name,
        "meal_type": plan.meal_type,
        "servings": plan.servings,
        "note": plan.note,
        "image": plan.image,
        "url": plan.url,
        "working_time": plan.working_time,
        "waiting_time": plan.waiting_time,
    }


def _plans_for(plans: list[MealPlanEntry] | None, day: date) -> list[MealPlanEntry]:
    return [p for p in plans or [] if p.plan_date == day]


def _state_for(plans: list[MealPlanEntry]) -> str | None:
    names = [p.name for p in plans if p.name]
    return ", ".join(names)[:255] if names else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TandoorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        [
            TandoorMealplanSensor(entry, "mealplan_today", 0, include_week=True),
            TandoorMealplanSensor(entry, "mealplan_tomorrow", 1),
            TandoorShoppingCountSensor(entry),
        ]
    )


class TandoorMealplanSensor(TandoorEntity, SensorEntity):
    """Shows what is planned for a specific day."""

    coordinator: TandoorMealplanCoordinator

    def __init__(
        self,
        entry: TandoorConfigEntry,
        key: str,
        day_offset: int,
        include_week: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(entry.runtime_data.mealplan, entry, key)
        self._attr_translation_key = key
        self._day_offset = day_offset
        self._include_week = include_week

    @property
    def native_value(self) -> str | None:
        """Names of the planned meals, comma separated."""
        day = dt_util.now().date() + timedelta(days=self._day_offset)
        return _state_for(_plans_for(self.coordinator.data, day))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Detailed meal data; the today sensor also carries the whole week."""
        today = dt_util.now().date()
        day = today + timedelta(days=self._day_offset)
        attrs: dict[str, Any] = {
            "meals": [_meal_dict(p) for p in _plans_for(self.coordinator.data, day)]
        }
        if self._include_week:
            attrs["days"] = [
                {
                    "date": (today + timedelta(days=offset)).isoformat(),
                    "meals": [
                        _meal_dict(p)
                        for p in _plans_for(
                            self.coordinator.data, today + timedelta(days=offset)
                        )
                    ],
                }
                for offset in range(MEALPLAN_DAYS)
            ]
        return attrs


class TandoorShoppingCountSensor(TandoorEntity, SensorEntity):
    """Number of open (unchecked) shopping list items."""

    _attr_translation_key = "shopping_items"

    coordinator: TandoorShoppingCoordinator

    def __init__(self, entry: TandoorConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(entry.runtime_data.shopping, entry, "shopping_items")

    @property
    def native_value(self) -> int:
        """Count of unchecked entries."""
        return sum(1 for e in self.coordinator.data or [] if not e.checked)
