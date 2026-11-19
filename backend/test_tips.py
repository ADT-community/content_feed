from fastapi.testclient import TestClient
from app import app, store, PLATFORM_FEE
from decimal import Decimal

client = TestClient(app)

def setup_function(function):
    # Reset store before each test
    store["tips"] = []
    store["balances"] = {}

def test_record_tip_basic():
    response = client.post("/tips", json={"creator_id": "creator1", "gross_amount": "100.00"})
    assert response.status_code == 200
    data = response.json()
    assert data["creator_share"] == "90.00"
    assert data["platform_fee"] == "10.00"

def test_record_tip_rounding():
    # 10.05 * 0.9 = 9.045 -> should round to 9.05
    response = client.post("/tips", json={"creator_id": "creator1", "gross_amount": "10.05"})
    assert response.status_code == 200
    data = response.json()
    assert data["creator_share"] == "9.05"
    assert data["platform_fee"] == "1.00"

def test_balance_endpoint():
    client.post("/tips", json={"creator_id": "creator1", "gross_amount": "100.00"})
    client.post("/tips", json={"creator_id": "creator1", "gross_amount": "50.00"})
    
    response = client.get("/me/balance?creator_id=creator1")
    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == "135.00"  # 90 + 45

def test_balance_endpoint_no_tips():
    response = client.get("/me/balance?creator_id=creator2")
    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == "0.00"

def test_invalid_gross_amount():
    response = client.post("/tips", json={"creator_id": "creator1", "gross_amount": "-10.00"})
    assert response.status_code == 400
