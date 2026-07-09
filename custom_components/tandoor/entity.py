"""Base entity for the Tandoor integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN
from .coordinator import TandoorConfigEntry


class TandoorEntity(CoordinatorEntity):
    """Common base for all Tandoor entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: TandoorConfigEntry,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Tandoor",
            manufacturer="Tandoor Recipes",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.runtime_data.client.base_url,
        )
