import pytest
import json
import os
import tempfile


@pytest.fixture(autouse=True)
def set_airlabs_api_key(monkeypatch):
    """
    Ensure AIRLABS_API_KEY is set for all tests so airlabs.py passes
    the key-present check and reaches the mocked requests.get call.
    Tests that specifically test the missing-key path use monkeypatch.delenv
    to override this fixture's value.
    """
    monkeypatch.setenv("AIRLABS_API_KEY", "test-dummy-key")


@pytest.fixture
def tmp_trip_dir(tmp_path):
    """Create a temporary trip directory with a budget.json."""
    trip_dir = tmp_path / "test-trip-2026-05"
    trip_dir.mkdir()
    budget = {
        "budget_usd": 3200,
        "items": []
    }
    (trip_dir / "budget.json").write_text(json.dumps(budget))
    return str(trip_dir)
