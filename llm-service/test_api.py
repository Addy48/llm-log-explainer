"""Unit tests for FastAPI endpoints."""
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "llm-service"

def test_explain_endpoint():
    payload = {
        "timestamp": "2026-06-30 12:00:00",
        "level": "ERROR",
        "message": "Database connection timeout after 30 seconds"
    }
    response = client.post("/explain", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "explanation" in res
    assert "log" in res

def test_timing_header_present():
    response = client.get("/health")
    assert "x-process-time-ms" in response.headers
