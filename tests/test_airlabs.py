import pytest
import os
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.airlabs import get_flight_status, AirLabsError


def test_get_flight_status_returns_structured_data():
    mock_response = {
        "response": {
            "flight_iata": "SQ321",
            "status": "en-route",
            "dep_time": "09:45",
            "arr_time": "17:30",
            "delayed": 0,
            "dep_terminal": "3",
            "dep_gate": "B12",
        }
    }
    with patch("tools.airlabs.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_response
        )
        result = get_flight_status("SQ321", "2026-05-14")

    assert result["flight_number"] == "SQ321"
    assert result["status"] == "en-route"
    assert result["delayed_minutes"] == 0
    assert result["gate"] == "B12"


def test_get_flight_status_raises_on_api_error():
    with patch("tools.airlabs.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=401,
            json=lambda: {"error": {"message": "Invalid API key"}}
        )
        with pytest.raises(AirLabsError, match="AirLabs API error"):
            get_flight_status("SQ321", "2026-05-14")


def test_get_flight_status_raises_if_no_api_key(monkeypatch):
    monkeypatch.delenv("AIRLABS_API_KEY", raising=False)
    with pytest.raises(AirLabsError, match="AIRLABS_API_KEY"):
        get_flight_status("SQ321", "2026-05-14")
