"""Shopping list text format: summary and description of a to-do item.

Pure functions without Home Assistant imports so they can be unit tested
(docs/spec/shopping-list.md).
"""

from __future__ import annotations

import re
from typing import Any

SUMMARY_AMOUNT_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s+(.+)$")
DESCRIPTION_AMOUNT_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*([^,]*)")


def _number(text: str) -> float:
    return float(text.replace(",", "."))


def format_amount_unit(amount: float, unit: str | None) -> str | None:
    """Return 'amount unit' ('2 kg', '3'), or None when both are empty."""
    parts: list[str] = []
    if amount:
        parts.append(f"{amount:g}")
    if unit:
        parts.append(unit)
    return " ".join(parts) or None


def format_summary(food: str, amount: float, unit: str | None) -> str:
    """Return the summary of the default format, e.g. '2 kg Mehl'."""
    return " ".join(p for p in (format_amount_unit(amount, unit), food) if p)


def parse_summary(summary: str | None) -> tuple[float, str]:
    """Split '2 Zwiebel' into amount and food name (default format)."""
    text = (summary or "").strip()
    if match := SUMMARY_AMOUNT_RE.match(text):
        return _number(match.group(1)), match.group(2).strip()
    return 0.0, text


def parse_description(description: str | None) -> tuple[float, str | None]:
    """Read '2 kg' or '2 kg, organic' into amount and unit."""
    text = (description or "").strip()
    if match := DESCRIPTION_AMOUNT_RE.match(text):
        return _number(match.group(1)), match.group(2).strip() or None
    return 0.0, None


def create_fields(
    summary: str | None, description: str | None, amount_in_description: bool
) -> tuple[str, float, str | None]:
    """Return (food, amount, unit) for a new item; food is '' when empty."""
    if amount_in_description:
        amount, unit = parse_description(description)
        return (summary or "").strip(), amount, unit
    amount, food = parse_summary(summary)
    return food, amount, None


def update_changes(
    *,
    entry_food: str,
    entry_amount: float,
    entry_unit: str | None,
    entry_checked: bool,
    item_summary: str | None,
    item_description: str | None,
    item_checked: bool,
    amount_in_description: bool,
) -> dict[str, Any]:
    """Return only the fields that changed; unit_name '' means remove the unit."""
    result: dict[str, Any] = {}
    if item_checked != entry_checked:
        result["checked"] = item_checked
    summary = (item_summary or "").strip()
    entry_food = (entry_food or "").strip()
    entry_unit = (entry_unit or "").strip() or None

    if not amount_in_description:
        if summary and summary != format_summary(entry_food, entry_amount, entry_unit):
            result["amount"], result["food_name"] = parse_summary(summary)
        return result

    if summary and summary != entry_food:
        result["food_name"] = summary
    description = (item_description or "").strip()
    if description != (format_amount_unit(entry_amount, entry_unit) or ""):
        amount, unit = parse_description(description)
        result["amount"] = amount
        result["unit_name"] = unit or ""
    return result
