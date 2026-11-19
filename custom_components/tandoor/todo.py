"""Todo platform for the Tandoor integration (shopping list)."""

from __future__ import annotations

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
from .const import CONF_SHOPPING_AMOUNT_IN_DESCRIPTION
from .coordinator import TandoorConfigEntry, TandoorShoppingCoordinator
from .entity import TandoorEntity
from .shopping_format import create_fields, update_changes

PARALLEL_UPDATES = 0

BASE_FEATURES = (
    TodoListEntityFeature.CREATE_TODO_ITEM
    | TodoListEntityFeature.UPDATE_TODO_ITEM
    | TodoListEntityFeature.DELETE_TODO_ITEM
)


def _convert_entry(entry: ShoppingEntry, amount_in_description: bool) -> TodoItem:
    """Convert a Tandoor shopping entry into a TodoItem (spec K2, K6)."""
    status = TodoItemStatus.COMPLETED if entry.checked else TodoItemStatus.NEEDS_ACTION
    if amount_in_description:
        return TodoItem(
            summary=entry.food_name,
            description=entry.amount_and_unit,
            uid=str(entry.entry_id),
            status=status,
        )
    return TodoItem(summary=entry.display, uid=str(entry.entry_id), status=status)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TandoorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the todo platform."""
    async_add_entities([TandoorShoppingListTodoEntity(entry)])


class TandoorShoppingListTodoEntity(TandoorEntity, TodoListEntity):
    """The Tandoor shopping list as a todo entity."""

    _attr_translation_key = "shopping_list"

    coordinator: TandoorShoppingCoordinator

    def __init__(self, entry: TandoorConfigEntry) -> None:
        """Initialize the todo entity; the format follows the entry option."""
        super().__init__(entry.runtime_data.shopping, entry, "shopping_list")
        self._amount_in_description = bool(
            entry.options.get(CONF_SHOPPING_AMOUNT_IN_DESCRIPTION, False)
        )
        self._attr_supported_features = BASE_FEATURES
        if self._amount_in_description:
            self._attr_supported_features |= (
                TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
            )

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the current shopping list items."""
        if self.coordinator.data is None:
            return None
        return [
            _convert_entry(e, self._amount_in_description)
            for e in self.coordinator.data
        ]

    def _entry_by_uid(self, uid: str | None) -> ShoppingEntry | None:
        return next(
            (e for e in self.coordinator.data or [] if str(e.entry_id) == uid), None
        )

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item to the shopping list."""
        food, amount, unit = create_fields(
            item.summary, item.description, self._amount_in_description
        )
        if not food:
            raise HomeAssistantError("Item name must not be empty")
        try:
            await self.coordinator.client.create_shopping_entry(food, amount, unit)
        except TandoorError as err:
            raise HomeAssistantError(f"Could not add item: {err}") from err
        await self.coordinator.async_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item; only changed fields are sent to Tandoor."""
        entry = self._entry_by_uid(item.uid)
        if entry is None:
            raise HomeAssistantError("Item not found on the shopping list")

        changes = update_changes(
            entry_food=entry.food_name,
            entry_amount=entry.amount,
            entry_unit=entry.unit_name,
            entry_checked=entry.checked,
            item_summary=item.summary,
            item_description=item.description,
            item_checked=item.status == TodoItemStatus.COMPLETED,
            amount_in_description=self._amount_in_description,
        )
        if not changes:
            return
        try:
            await self.coordinator.client.update_shopping_entry(
                entry.entry_id, **changes
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
