"""Minimal async client for the Tandoor Recipes API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import aiohttp


class TandoorError(Exception):
    """Base error for the Tandoor client."""


class TandoorConnectionError(TandoorError):
    """Tandoor is unreachable or returned an unexpected status."""


class TandoorAuthenticationError(TandoorError):
    """The API token was rejected."""


@dataclass
class ShoppingEntry:
    """A single entry on the Tandoor shopping list."""

    entry_id: int
    food_name: str
    amount: float
    unit_name: str | None
    checked: bool

    @property
    def display(self) -> str:
        """Human readable representation, e.g. '2 kg Mehl'."""
        parts: list[str] = []
        if self.amount:
            parts.append(f"{self.amount:g}")
        if self.unit_name:
            parts.append(self.unit_name)
        parts.append(self.food_name)
        return " ".join(parts)


@dataclass
class MealPlanEntry:
    """A single meal plan entry."""

    plan_id: int
    plan_date: date
    name: str
    meal_type: str | None
    servings: float | None
    note: str | None
    recipe_id: int | None
    image: str | None
    url: str | None
    working_time: int
    waiting_time: int


@dataclass
class Space:
    """The Tandoor space (instance metadata)."""

    space_id: int
    name: str


@dataclass
class TandoorClient:
    """Thin async wrapper around the Tandoor REST API."""

    base_url: str
    api_token: str
    session: aiohttp.ClientSession
    request_timeout: float = 15.0
    _headers: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {self.api_token}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Perform an API request and return the decoded JSON body."""
        try:
            async with self.session.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=self.request_timeout),
            ) as resp:
                if resp.status in (401, 403):
                    raise TandoorAuthenticationError("Invalid API token")
                if resp.status >= 400:
                    body = await resp.text()
                    raise TandoorConnectionError(
                        f"HTTP {resp.status} for {path}: {body[:200]}"
                    )
                if resp.status == 204:
                    return None
                return await resp.json()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise TandoorConnectionError(str(err)) from err

    @staticmethod
    def _results(data: Any) -> list[dict[str, Any]]:
        """Unwrap paginated ({'results': [...]}) and plain list responses."""
        if isinstance(data, dict):
            return data.get("results", [])
        return data or []

    async def get_space(self) -> Space:
        """Return the first space, used for connection validation."""
        data = self._results(await self._request("GET", "/api/space/"))
        if not data:
            raise TandoorConnectionError("No space returned")
        return Space(space_id=data[0]["id"], name=data[0].get("name") or "Tandoor")

    async def get_shopping_entries(self) -> list[ShoppingEntry]:
        """Return open and recently checked shopping list entries."""
        data = self._results(
            await self._request(
                "GET", "/api/shopping-list-entry/", params={"checked": "recent"}
            )
        )
        return [
            ShoppingEntry(
                entry_id=e["id"],
                food_name=(e.get("food") or {}).get("name") or "",
                amount=e.get("amount") or 0.0,
                unit_name=(e.get("unit") or {}).get("name"),
                checked=bool(e.get("checked")),
            )
            for e in data
            if e.get("food")
        ]

    async def create_shopping_entry(
        self, food_name: str, amount: float = 0.0, unit_name: str | None = None
    ) -> None:
        """Create a shopping list entry."""
        payload: dict[str, Any] = {
            "food": {"name": food_name},
            "amount": amount,
            "unit": {"name": unit_name} if unit_name else None,
        }
        await self._request("POST", "/api/shopping-list-entry/", json=payload)

    async def update_shopping_entry(
        self,
        entry_id: int,
        *,
        checked: bool | None = None,
        food_name: str | None = None,
        amount: float | None = None,
        unit_name: str | None = None,
    ) -> None:
        """Update fields of a shopping list entry."""
        payload: dict[str, Any] = {}
        if checked is not None:
            payload["checked"] = checked
        if food_name is not None:
            payload["food"] = {"name": food_name}
        if amount is not None:
            payload["amount"] = amount
        if unit_name is not None:
            payload["unit"] = {"name": unit_name}
        if payload:
            await self._request(
                "PATCH", f"/api/shopping-list-entry/{entry_id}/", json=payload
            )

    async def delete_shopping_entry(self, entry_id: int) -> None:
        """Delete a shopping list entry."""
        await self._request("DELETE", f"/api/shopping-list-entry/{entry_id}/")

    async def get_meal_plans(self, start: date, end: date) -> list[MealPlanEntry]:
        """Return meal plan entries between start and end (inclusive)."""
        data = self._results(
            await self._request(
                "GET",
                "/api/meal-plan/",
                params={"from_date": start.isoformat(), "to_date": end.isoformat()},
            )
        )
        plans: list[MealPlanEntry] = []
        for p in data:
            recipe = p.get("recipe") or {}
            image = recipe.get("image")
            if image and not str(image).startswith("http"):
                image = f"{self.base_url}{image}"
            plans.append(
                MealPlanEntry(
                    plan_id=p["id"],
                    plan_date=date.fromisoformat(p["from_date"][:10]),
                    name=recipe.get("name") or p.get("title") or p.get("note") or "",
                    meal_type=(p.get("meal_type") or {}).get("name"),
                    servings=p.get("servings"),
                    note=p.get("note") or None,
                    recipe_id=recipe.get("id"),
                    image=image,
                    url=(
                        f"{self.base_url}/view/recipe/{recipe['id']}"
                        if recipe.get("id")
                        else None
                    ),
                    working_time=recipe.get("working_time") or 0,
                    waiting_time=recipe.get("waiting_time") or 0,
                )
            )
        plans.sort(key=lambda p: (p.plan_date, p.plan_id))
        return plans
