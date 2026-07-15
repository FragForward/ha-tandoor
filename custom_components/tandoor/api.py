"""Minimal async client for the Tandoor Recipes API."""

from __future__ import annotations

import asyncio
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
    rating: float | None = None


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

    def _abs_url(self, path: str | None) -> str | None:
        """Turn a relative media/API path into an absolute URL."""
        if not path:
            return None
        return path if str(path).startswith("http") else f"{self.base_url}{path}"

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
            plans.append(
                MealPlanEntry(
                    plan_id=p["id"],
                    plan_date=date.fromisoformat(p["from_date"][:10]),
                    name=recipe.get("name") or p.get("title") or p.get("note") or "",
                    meal_type=(p.get("meal_type") or {}).get("name"),
                    servings=p.get("servings"),
                    note=p.get("note") or None,
                    recipe_id=recipe.get("id"),
                    image=self._abs_url(recipe.get("image")),
                    url=(
                        f"{self.base_url}/view/recipe/{recipe['id']}"
                        if recipe.get("id")
                        else None
                    ),
                    working_time=recipe.get("working_time") or 0,
                    waiting_time=recipe.get("waiting_time") or 0,
                    rating=recipe.get("rating"),
                )
            )
        plans.sort(key=lambda p: (p.plan_date, p.plan_id))
        await self._fill_missing_ratings(plans)
        return plans

    async def _fill_missing_ratings(self, plans: list[MealPlanEntry]) -> None:
        """Load per-recipe ratings the meal-plan endpoint did not embed.

        The /api/meal-plan/ recipe object is not annotated with the (per-user
        average) rating, so fetch it once per distinct recipe and cache it onto
        every plan entry that shares that recipe.
        """
        missing = {
            p.recipe_id
            for p in plans
            if p.recipe_id and p.rating is None
        }
        if not missing:
            return
        results = await asyncio.gather(
            *(self.get_recipe_rating(rid) for rid in missing),
            return_exceptions=True,
        )
        ratings = {
            rid: res
            for rid, res in zip(missing, results)
            if not isinstance(res, Exception)
        }
        for p in plans:
            if p.rating is None and p.recipe_id in ratings:
                p.rating = ratings[p.recipe_id]

    async def get_recipe(self, recipe_id: int) -> dict[str, Any]:
        """Return a trimmed recipe detail for the card popup.

        Includes the (per-user) rating, absolute image URL and the steps with
        their ingredients so the recipe can be rendered without opening Tandoor.
        """
        data = await self._request("GET", f"/api/recipe/{recipe_id}/")
        steps: list[dict[str, Any]] = []
        for step in data.get("steps") or []:
            ingredients: list[dict[str, Any]] = []
            for ing in step.get("ingredients") or []:
                if ing.get("is_header"):
                    ingredients.append({"header": (ing.get("note") or "").strip()})
                    continue
                ingredients.append(
                    {
                        "amount": ing.get("amount") or 0,
                        "unit": (ing.get("unit") or {}).get("name") or "",
                        "food": (ing.get("food") or {}).get("name") or "",
                        "note": ing.get("note") or "",
                    }
                )
            steps.append(
                {
                    "name": (step.get("name") or "").strip(),
                    "instruction": step.get("instruction") or "",
                    "ingredients": ingredients,
                }
            )
        return {
            "id": data.get("id"),
            "name": data.get("name") or "",
            "description": data.get("description") or "",
            "image": self._abs_url(data.get("image")),
            "servings": data.get("servings"),
            "working_time": data.get("working_time") or 0,
            "waiting_time": data.get("waiting_time") or 0,
            "source_url": data.get("source_url") or None,
            "url": f"{self.base_url}/view/recipe/{recipe_id}",
            "rating": data.get("rating"),
            "steps": steps,
        }

    async def get_recipe_rating(self, recipe_id: int) -> float | None:
        """Return the (per-user average) rating of a single recipe."""
        data = await self._request("GET", f"/api/recipe/{recipe_id}/")
        return data.get("rating")

    async def set_rating(self, recipe_id: int, rating: int | None) -> None:
        """Set the recipe rating by writing to the user's cook log.

        Tandoor stores ratings only on CookLog entries (the recipe rating is the
        per-user average). We keep the behaviour "one settable value" by
        overwriting the most recent existing cook-log entry for this recipe, and
        only create a new one when none exists yet.
        """
        if rating is not None:
            rating = max(0, min(5, int(rating)))
        entries = self._results(
            await self._request(
                "GET", "/api/cook-log/", params={"recipe": recipe_id}
            )
        )
        if entries:
            target = max(
                entries,
                key=lambda e: e.get("updated_at") or e.get("created_at") or "",
            )
            await self._request(
                "PATCH", f"/api/cook-log/{target['id']}/", json={"rating": rating}
            )
            return
        await self._request(
            "POST",
            "/api/cook-log/",
            json={"recipe": recipe_id, "rating": rating},
        )
