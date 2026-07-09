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

AMOUNT_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s+(.+)$")


def _parse_summary(summary: str) -> tuple[float, str]:
    """Split '2 Zwiebel' into amount and food name."""
    text = (summary or "").strip()
    if match := AMOUNT_RE.match(text):
        return float(match.group(1).replace(",", ".")), match.group(2).strip()
    return 0.0, text


def _convert_entry(entry: ShoppingEntry) -> TodoItem:
    """Convert a Tandoor shopping entry into a TodoItem."""
    return TodoItem(
        summary=entry.display,
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
        amount, food = _parse_summary(item.summary or "")
        if not food:
            raise HomeAssistantError("Item name must not be empty")
        try:
            await self.coordinator.client.create_shopping_entry(food, amount)
        except TandoorError as err:
            raise HomeAssistantError(f"Could not add item: {err}") from err
        await self.coordinator.async_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item (check off / rename)."""
        entry = self._entry_by_uid(item.uid)
        if entry is None:
            raise HomeAssistantError("Item not found on the shopping list")

        checked = item.status == TodoItemStatus.COMPLETED
        food_name: str | None = None
        amount: float | None = None
        if item.summary and item.summary.strip() != entry.display:
            amount, food_name = _parse_summary(item.summary)

        try:
            await self.coordinator.client.update_shopping_entry(
                entry.entry_id,
                checked=checked if checked != entry.checked else None,
                food_name=food_name,
                amount=amount,
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
