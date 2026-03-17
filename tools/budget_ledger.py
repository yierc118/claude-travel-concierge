"""
Budget ledger — read/write budget.json for a trip.
"""
import json
import os
from datetime import datetime, timezone

ITEM_TYPES = {"flight", "accommodation", "food", "transport", "activities", "other"}


def _read(trip_dir: str) -> dict:
    path = os.path.join(trip_dir, "budget.json")
    with open(path) as f:
        return json.load(f)


def _write(trip_dir: str, data: dict) -> None:
    path = os.path.join(trip_dir, "budget.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def add_item(trip_dir: str, category: str, description: str, amount: float, item_type: str) -> None:
    """
    Add a budget item.
    category: one of ITEM_TYPES
    item_type: 'confirmed' | 'estimate'
    """
    if category not in ITEM_TYPES:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {ITEM_TYPES}")
    if item_type not in ("confirmed", "estimate"):
        raise ValueError(f"Invalid item_type '{item_type}'. Must be 'confirmed' or 'estimate'.")

    data = _read(trip_dir)
    data["items"].append({
        "category": category,
        "description": description,
        "amount": amount,
        "type": item_type,
        "added": datetime.now(timezone.utc).isoformat(),
    })
    _write(trip_dir, data)


def get_summary(trip_dir: str) -> dict:
    """Return budget summary: committed, estimated_total, remaining."""
    data = _read(trip_dir)
    committed = sum(i["amount"] for i in data["items"] if i["type"] == "confirmed")
    estimated_total = sum(i["amount"] for i in data["items"])
    return {
        "budget_usd": data["budget_usd"],
        "committed": committed,
        "estimated_total": estimated_total,
        "remaining": data["budget_usd"] - estimated_total,
        "items": data["items"],
    }
