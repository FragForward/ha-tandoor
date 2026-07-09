"""Calendar platform for the Tandoor integration (meal plan)."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import MealPlanEntry, TandoorError
from .coordinator import TandoorConfigEntry, TandoorMealplanCoordinator
from .entity import TandoorEntity

PARALLEL_UPDATES = 0


def _convert_plan(plan: MealPlanEntry) -> CalendarEvent:
    """Convert a meal plan entry into an all-day calendar event."""
    summary = f"{plan.meal_type}: {plan.name}" if plan.meal_type else plan.name
    return CalendarEvent(
        summary=summary,
        start=plan.plan_date,
        end=plan.plan_date + timedelta(days=1),
        description=plan.note,
        location=None,
        uid=str(plan.plan_id),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TandoorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the calendar platform."""
    async_add_entities([TandoorMealplanCalendarEntity(entry)])


class TandoorMealplanCalendarEntity(TandoorEntity, CalendarEntity):
    """The Tandoor meal plan as a calendar."""

    _attr_translation_key = "mealplan"

    coordinator: TandoorMealplanCoordinator

    def __init__(self, entry: TandoorConfigEntry) -> None:
        """Initialize the calendar entity."""
        super().__init__(entry.runtime_data.mealplan, entry, "mealplan")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming meal."""
        today = dt_util.now().date()
        upcoming = [p for p in self.coordinator.data or [] if p.plan_date >= today]
        if not upcoming:
            return None
        return _convert_plan(upcoming[0])

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return meal plan events in a specific date range."""
        try:
            plans = await self.coordinator.client.get_meal_plans(
                start_date.date(), end_date.date()
            )
        except TandoorError:
            return []
        return [_convert_plan(p) for p in plans]
