import pytest
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.budget_ledger import add_item, get_summary, ITEM_TYPES


def test_add_confirmed_item(tmp_trip_dir):
    add_item(tmp_trip_dir, "flight", "SQ321 SIN→NRT", 487, "confirmed")
    with open(os.path.join(tmp_trip_dir, "budget.json")) as f:
        data = json.load(f)
    assert len(data["items"]) == 1
    assert data["items"][0]["amount"] == 487
    assert data["items"][0]["type"] == "confirmed"


def test_add_estimate_item(tmp_trip_dir):
    add_item(tmp_trip_dir, "food", "Daily food budget", 50, "estimate")
    with open(os.path.join(tmp_trip_dir, "budget.json")) as f:
        data = json.load(f)
    assert data["items"][0]["type"] == "estimate"


def test_summary_separates_confirmed_from_estimates(tmp_trip_dir):
    add_item(tmp_trip_dir, "flight", "SQ321", 487, "confirmed")
    add_item(tmp_trip_dir, "food", "Food", 400, "estimate")
    summary = get_summary(tmp_trip_dir)
    assert summary["budget_usd"] == 3200
    assert summary["committed"] == 487
    assert summary["estimated_total"] == 887
    assert summary["remaining"] == 3200 - 887


def test_invalid_item_type_raises(tmp_trip_dir):
    with pytest.raises(ValueError, match="Invalid category"):
        add_item(tmp_trip_dir, "invalid_category", "Test", 100, "confirmed")
