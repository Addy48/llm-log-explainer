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


def test_explain_uses_the_log_content():
    db = client.post("/explain", json={"level": "ERROR", "message": "Database connection failed after 5 retry attempts"}).json()
    disk = client.post("/explain", json={"level": "ERROR", "message": "Disk I/O error: read failure on sector 0x7F3A2B1C"}).json()
    assert db["explanation"]["category"] == "database"
    assert disk["explanation"]["category"] == "storage"
    assert db["explanation"]["severity"] == "HIGH"
    assert 0 < db["explanation"]["confidence"] <= 1


def test_info_log_is_low_severity():
    res = client.post("/explain", json={"level": "INFO", "message": "Server started successfully on port 8080"}).json()
    assert res["explanation"]["severity"] == "LOW"


def test_batch_returns_incident_summary():
    logs = [
        {"level": "WARNING", "message": "Memory usage trending upward: 72% (368MB/512MB)"},
        {"level": "ERROR", "message": "OutOfMemoryError: Java heap space exhausted"},
        {"level": "ERROR", "message": "Application crash: initiating emergency restart"},
    ]
    res = client.post("/explain-batch", json={"logs": logs}).json()
    assert res["count"] == 3
    assert res["incident"]["category"] == "memory"
    assert res["incident"]["status"] == "critical"
    assert res["root_cause"]


def test_analyze_text_parses_common_formats():
    text = "\n".join([
        "2026-10-26T10:00:00Z ERROR Connection refused to Redis server at 127.0.0.1:6379",
        "[WARN] Disk space running low: 15% remaining on /dev/sda1",
        '{"level": "info", "message": "User login successful: user_id=12847"}',
        "081111 085924 27 INFO dfs.FSNamesystem: BLOCK* NameSystem.delete: blk_1 is added to invalidSet",
    ])
    res = client.post("/analyze-text", json={"text": text}).json()
    levels = [e["log"]["level"] for e in res["explanations"]]
    assert levels == ["ERROR", "WARNING", "INFO", "INFO"]
    assert res["explanations"][0]["explanation"]["category"] == "cache"


def test_analyze_text_rejects_empty():
    assert client.post("/analyze-text", json={"text": "   \n  "}).status_code == 400


def test_terms_match_on_word_boundaries():
    res = client.post("/explain", json={"level": "INFO", "message": "Request processed in 145ms: GET /api/orders"}).json()
    assert res["explanation"]["category"] != "storage"
