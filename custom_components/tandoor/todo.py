"""Todo platform for the Tandoor integration (shopping list)."""

from __future__ import annotations

import re

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import ShoppingEntry, TandoorError
from .coordinator import TandoorConfigEntry, TandoorShoppingCoordinator
from .entity import TandoorEntity

PARALLEL_UPDATES = 0

DESCRIPTION_AMOUNT_RE = re.compile(r"^(?P<amount>\d+(?:[.,]\d+)?)\s+(?P<unit>.{0,10}),")

def _parse_description(description: str) -> tuple[float, str]:
    """Split '2 kg' into amount and unit name."""
    text = (description or "").strip()
    if match := DESCRIPTION_AMOUNT_RE.match(text):
        return float(match.group('amount').replace(",", ".")), match.group('unit').strip()
    return 0.0, ""


def _convert_entry(entry: ShoppingEntry) -> TodoItem:
    """Convert a Tandoor shopping entry into a TodoItem."""
    return TodoItem(
        summary=entry.food_name,
        description=entry.amount_and_unit,
        uid=str(entry.entry_id),
        status=(
            TodoItemStatus.COMPLETED if entry.checked else TodoItemStatus.NEEDS_ACTION
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TandoorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the todo platform."""
    async_add_entities([TandoorShoppingListTodoEntity(entry)])


class TandoorShoppingListTodoEntity(TandoorEntity, TodoListEntity):
    """The Tandoor shopping list as a todo entity."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )
    _attr_translation_key = "shopping_list"

    coordinator: TandoorShoppingCoordinator

    def __init__(self, entry: TandoorConfigEntry) -> None:
        """Initialize the todo entity."""
        super().__init__(entry.runtime_data.shopping, entry, "shopping_list")

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the current shopping list items."""
        if self.coordinator.data is None:
            return None
        return [_convert_entry(e) for e in self.coordinator.data]

    def _entry_by_uid(self, uid: str | None) -> ShoppingEntry | None:
        return next(
            (e for e in self.coordinator.data or [] if str(e.entry_id) == uid), None
        )

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item to the shopping list."""
        summary = (item.summary or "").strip()
        amount, unit_name = _parse_description(item.description or "")
        if not summary:
            raise HomeAssistantError("Item name must not be empty")
        try:
            await self.coordinator.client.create_shopping_entry(summary, amount, unit_name)
        except TandoorError as err:
            raise HomeAssistantError(f"Could not add item: {err}") from err
        await self.coordinator.async_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item (check off / rename)."""
        entry = self._entry_by_uid(item.uid)
        if entry is None:
            raise HomeAssistantError("Item not found on the shopping list")

        checked = item.status == TodoItemStatus.COMPLETED
        amount: float | None = None
        unit_name: str | None = None

        if item.description:
            amount, unit_name = _parse_description(item.description)

        if amount == entry.amount:
            amount = None  # No change in amount
        if unit_name == entry.unit_name:
            unit_name = None  # No change in unit name

        try:
            await self.coordinator.client.update_shopping_entry(
                entry.entry_id,
                checked=checked if checked != entry.checked else None,
                food_name=item.summary,
                amount=amount,
                unit_name=unit_name
            )
        except TandoorError as err:
            raise HomeAssistantError(f"Could not update item: {err}") from err
        await self.coordinator.async_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items from the shopping list."""
        try:
            for uid in uids:
                await self.coordinator.client.delete_shopping_entry(int(uid))
        except TandoorError as err:
            raise HomeAssistantError(f"Could not delete item: {err}") from err
        await self.coordinator.async_refresh()
