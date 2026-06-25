from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import MOCK_SHIPMENTS, app

client = TestClient(app)

AUTH_HEADERS = {"X-API-Key": "techstar-fde-key-001"}


# ============================================================
# TASK 1: Auth tests
# ============================================================


def test_missing_api_key_returns_401():
    response = client.get("/shipments")  # No headers at all
    assert response.status_code == 401


def test_invalid_api_key_returns_403():
    response = client.get("/shipments", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403


# ============================================================
# TASK 2: Shipment CRUD tests
# ============================================================


def test_list_shipments_returns_all():
    response = client.get("/shipments", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == len(MOCK_SHIPMENTS)


def test_list_shipments_filters_by_status():
    response = client.get("/shipments?status=delayed", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert all(s["status"] == "delayed" for s in response.json())


def test_list_shipments_filters_by_carrier():
    response = client.get("/shipments?carrier=dhl", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert all(s["carrier"] == "DHL" for s in response.json())


def test_get_shipment_success():
    response = client.get("/shipments/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["shipment_id"] == "SH001"


def test_get_shipment_not_found_returns_404():
    response = client.get("/shipments/NONEXISTENT", headers=AUTH_HEADERS)
    assert response.status_code == 404


def test_create_shipment_success():
    payload = {
        "shipment_id": "SH999",
        "carrier": "dhl",
        "origin": "Mumbai",
        "destination": "Pune",
        "cost_usd": 99.0,
    }
    response = client.post("/shipments", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 201
    assert response.json()["carrier"] == "DHL"


def test_create_shipment_invalid_carrier_returns_422():
    payload = {
        "shipment_id": "SH998",
        "carrier": "UPS",
        "origin": "Mumbai",
        "destination": "Pune",
        "cost_usd": 99.0,
    }
    response = client.post("/shipments", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_create_shipment_duplicate_id_returns_409():
    payload = {
        "shipment_id": "SH001",
        "carrier": "DHL",  # already exists
        "origin": "Mumbai",
        "destination": "Pune",
        "cost_usd": 50.0,
    }
    response = client.post("/shipments", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 409


def test_list_carriers_returns_all():
    response = client.get("/carriers", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == 3


# ============================================================
# TASK 3: Aggregation endpoint tests with mocked vendors
# ============================================================


@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_all_vendors_succeed(mock_a, mock_b, mock_c):
    """When all 3 vendors respond, expect all 3 normalised results."""
    mock_a.return_value = {"id": "SH001", "current_status": "in_transit"}
    mock_b.return_value = {"shipmentRef": "SH001", "trackingState": "DELAYED"}
    mock_c.return_value = {
        "shipment": {"identifier": "SH001", "state": {"code": "DELIVERED"}}
    }

    response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == 3


@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_one_vendor_fails(mock_a, mock_b, mock_c):
    """Vendor B failing should still return 200 with 2 results, not 500."""
    mock_a.return_value = {"id": "SH001", "current_status": "in_transit"}
    mock_b.side_effect = ConnectionError("Vendor B timeout")
    mock_c.return_value = {
        "shipment": {"identifier": "SH001", "state": {"code": "DELIVERED"}}
    }

    response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == 2


@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_all_vendors_fail_returns_503(mock_a, mock_b, mock_c):
    """If every vendor fails, the endpoint must return 503, not an empty 200 list."""
    mock_a.side_effect = ConnectionError("down")
    mock_b.side_effect = ConnectionError("down")
    mock_c.side_effect = ConnectionError("down")

    response = client.get("/supply-chain-status/SH001", headers=AUTH_HEADERS)
    assert response.status_code == 503
