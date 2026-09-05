"""Unit tests for synthetic log generator."""
import pytest
from app import app, SCENARIOS, generate_scenario_logs

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json['status'] == 'healthy'

def test_generate_scenario_logs():
    for name in SCENARIOS.keys():
        logs = generate_scenario_logs(name)
        assert logs is not None
        assert len(logs) > 0
        for entry in logs:
            assert 'timestamp' in entry
            assert 'level' in entry
            assert 'message' in entry
