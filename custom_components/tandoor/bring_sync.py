"""Automatic Bring return channel for the Kochliste.

Watches the Bring shopping list (a todo entity in Home Assistant): as soon
as every SENT ingredient of a Kochliste recipe is checked off there (no
longer "needs_action"), the recipe is marked "kochbar" on the Essensplan
website automatically. Matching is by item name (case-insensitive) because
Bring does not carry our ingredient IDs; it fails safe — a rename in Bring
just means the recipe stays in shopping state until marked manually.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .api import EssensplanClient, EssensplanError
from .coordinator import TandoorKochlisteCoordinator

_LOGGER = logging.getLogger(__name__)

CHECK_INTERVAL = timedelta(minutes=15)


class TandoorBringSync:
    """Marks Kochliste recipes cookable once their Bring items are checked."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EssensplanClient,
        bring_entity: str,
        kochliste: TandoorKochlisteCoordinator,
    ) -> None:
        """Initialize the sync helper."""
        self._hass = hass
        self._client = client
        self._bring_entity = bring_entity
        self._kochliste = kochliste
        self._lock = asyncio.Lock()
        self._unsubs: list = []

    @callback
    def async_setup(self) -> None:
        """Start listening for Bring list changes (+ periodic safety net)."""
        self._unsubs.append(
            async_track_state_change_event(
                self._hass, [self._bring_entity], self._on_change
            )
        )
        self._unsubs.append(
            async_track_time_interval(self._hass, self._on_interval, CHECK_INTERVAL)
        )

    @callback
    def async_teardown(self) -> None:
        """Stop all listeners (entry unload/reload)."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    @callback
    def _on_change(self, event: Event) -> None:
        self._hass.async_create_task(self.async_check())

    async def _on_interval(self, now) -> None:
        await self.async_check()

    async def async_check(self) -> None:
        """Run one comparison; never raise into Home Assistant."""
        if self._lock.locked():
            return
        async with self._lock:
            try:
                await self._check()
            except EssensplanError as err:
                _LOGGER.warning("Bring sync: Essensplan API error: %s", err)
            except Exception:  # noqa: BLE001 - sync must never break HA
                _LOGGER.exception("Bring sync failed")

    async def _check(self) -> None:
        data = await self._client.einkauf()
        bring_kids = {str(k) for k in data.get("bring_rezepte") or []}
        if not bring_kids:
            return
        result = await self._hass.services.async_call(
            "todo",
            "get_items",
            {"entity_id": self._bring_entity},
            blocking=True,
            return_response=True,
        )
        lists = (result or {}).get(self._bring_entity) or {}
        open_names = {
            str(item.get("summary") or "").strip().lower()
            for item in lists.get("items") or []
            if item.get("status") == "needs_action"
        }
        zutaten = data.get("zutaten") or []
        done_any = False
        for rezept in data.get("rezepte") or []:
            kid = str(rezept.get("id") or "")
            if kid not in bring_kids:
                continue
            sent = [
                z
                for z in zutaten
                if not z.get("onhand")
                and z.get("gesendet")
                and any(
                    v.get("kid") == kid for v in z.get("verwendungen") or []
                )
            ]
            if not sent:
                continue
            still_open = [
                z
                for z in sent
                if str(z.get("name") or "").strip().lower() in open_names
            ]
            if still_open:
                continue
            _LOGGER.info(
                "Bring sync: all items for '%s' checked off -> kochbar",
                rezept.get("titel"),
            )
            await self._client.kochliste_kochbar(kid)
            done_any = True
        if done_any:
            await self._kochliste.async_request_refresh()
