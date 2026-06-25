import json
import pytest
from unittest.mock import patch, MagicMock

from pydantic import BaseModel, Field, ValidationError

from day5_ex2_logistics_client import (
    LogisticsAPIClient,
    APIClientError,
    RateLimitError,
)

# ============================================================
# TASK 1: Pydantic schema for response contract testing + fixture
# ============================================================


class ShipmentSchema(BaseModel):
    """The contract: what a valid shipment response MUST look like."""

    shipment_id: str = Field(..., min_length=3)
    carrier: str
    status: str
    delay_days: int = Field(..., ge=0)


@pytest.fixture
def client() -> LogisticsAPIClient:
    """A client configured with a valid test API key."""
    return LogisticsAPIClient(
        base_url="https://api.carrier-platform.in",
        api_key="valid-test-key-123",
    )


# ============================================================
# TASK 2A: Successful call returns correctly shaped data
# ============================================================


@patch("day5_ex2_logistics_client.mock_http_get")
def test_get_shipment_success_returns_valid_schema(mock_get, client):
    """A 200 response should parse and match the ShipmentSchema contract."""
    mock_get.return_value = (
        200,
        json.dumps(
            {
                "shipment_id": "SH-100",
                "carrier": "FedEx",
                "status": "delivered",
                "delay_days": 0,
            }
        ),
    )

    result = client.get_shipment("SH-100")

    assert result["shipment_id"] == "SH-100"
    ShipmentSchema.model_validate(result)
    assert mock_get.call_count == 1


# ============================================================
# TASK 2B: Schema contract test catches a missing field
# ============================================================


def test_shipment_schema_rejects_missing_field():
    """If the vendor drops a required field, our contract test must fail."""
    incomplete = {"carrier": "DHL", "status": "in_transit", "delay_days": 1}

    with pytest.raises(ValidationError):
        ShipmentSchema.model_validate(incomplete)


# ============================================================
# TASK 3A: Retry on 500 then success
# ============================================================


@patch("day5_ex2_logistics_client.time.sleep")
@patch("day5_ex2_logistics_client.mock_http_get")
def test_retries_on_500_then_succeeds(mock_get, mock_sleep, client):
    """Client should retry once on a 500, then succeed on the second attempt."""
    mock_get.side_effect = [
        (500, json.dumps({"error": "Internal error"})),
        (
            200,
            json.dumps(
                {
                    "shipment_id": "SH-200",
                    "carrier": "DHL",
                    "status": "in_transit",
                    "delay_days": 0,
                }
            ),
        ),
    ]

    result = client.get_shipment("SH-200")

    assert result["shipment_id"] == "SH-200"
    assert mock_get.call_count == 2
    assert mock_sleep.called


# ============================================================
# TASK 3B: Rate limit (429) is respected
# ============================================================


@patch("day5_ex2_logistics_client.time.sleep")
@patch("day5_ex2_logistics_client.mock_http_get")
def test_rate_limit_retries_after_wait(mock_get, mock_sleep, client):
    """A 429 with retry_after should cause exactly one sleep call, then succeed."""
    mock_get.side_effect = [
        (429, json.dumps({"error": "Rate limited", "retry_after": 3})),
        (
            200,
            json.dumps(
                {
                    "shipment_id": "SH-300",
                    "carrier": "BlueDart",
                    "status": "delivered",
                    "delay_days": 0,
                }
            ),
        ),
    ]

    result = client.get_shipment("SH-300")

    assert result["shipment_id"] == "SH-300"
    mock_sleep.assert_called_with(3)


# ============================================================
# TASK 3C: 401 must NOT be retried
# ============================================================


@patch("day5_ex2_logistics_client.mock_http_get")
def test_invalid_api_key_fails_without_retry(mock_get, client):
    """A 401 is a permanent failure — must raise immediately, no retries."""
    mock_get.return_value = (401, json.dumps({"error": "Invalid API key"}))

    with pytest.raises(APIClientError):
        client.get_shipment("SH-400")

    assert mock_get.call_count == 1


# ============================================================
# TASK 3D: Parametrized test across multiple 5xx codes
# ============================================================


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
@patch("day5_ex2_logistics_client.time.sleep")
@patch("day5_ex2_logistics_client.mock_http_get")
def test_all_5xx_codes_are_retriable(mock_get, mock_sleep, status_code, client):
    """Every 5xx status should trigger the retry path, not an immediate raise."""
    mock_get.side_effect = [
        (status_code, json.dumps({"error": "Server error"})),
        (
            200,
            json.dumps(
                {
                    "shipment_id": "SH-500",
                    "carrier": "DHL",
                    "status": "pending",
                    "delay_days": 0,
                }
            ),
        ),
    ]

    result = client.get_shipment("SH-500")

    assert result["shipment_id"] == "SH-500"
    assert mock_get.call_count == 2


# ============================================================
# EXTRA: Unexpected status code falls through to else branch
# ============================================================


@patch("day5_ex2_logistics_client.mock_http_get")
def test_unexpected_status_code_raises_api_client_error(mock_get, client):
    """A status code outside 200/429/401/403/5xx should still raise APIClientError."""
    mock_get.return_value = (418, json.dumps({"error": "I'm a teapot"}))

    with pytest.raises(APIClientError):
        client.get_shipment("SH-999")

    assert mock_get.call_count == 1
