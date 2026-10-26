import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("incident_drill.py")


def load_drill_module():
    spec = importlib.util.spec_from_file_location("incident_drill", MODULE_PATH)
    assert spec is not None, "incident drill module should exist"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def database_result():
    return {
        "count": 10,
        "incident": {
            "category": "database",
            "status": "critical",
            "health_score": 40,
            "severity_counts": {"HIGH": 2, "MEDIUM": 4, "LOW": 4},
            "root_cause": "Database server became unreachable.",
            "recommended_actions": ["Check database health", "Verify network routing"],
        },
    }


def test_critical_scenario_is_reported_as_simulated_release_block():
    drill = load_drill_module()

    assessment = drill.evaluate_incident("database_failure", database_result())

    assert assessment["expected_category"] == "database"
    assert assessment["gate_decision"] == "BLOCKED"
    assert assessment["validation"] == "passed"


def test_wrong_diagnosis_fails_the_drill():
    drill = load_drill_module()
    result = database_result()
    result["incident"]["category"] = "storage"

    with pytest.raises(drill.IncidentDrillError, match="expected category 'database'"):
        drill.evaluate_incident("database_failure", result)


def test_report_explains_why_release_was_blocked():
    drill = load_drill_module()
    assessment = drill.evaluate_incident("database_failure", database_result())

    report = drill.format_report(assessment)

    assert "**Simulated release gate:** **BLOCKED**" in report
    assert "Database server became unreachable." in report
    assert "Check database health" in report


def test_release_gate_rejects_status_that_disagrees_with_severity_counts():
    drill = load_drill_module()
    result = database_result()
    result["incident"]["status"] = "stable"

    with pytest.raises(drill.IncidentDrillError, match="status 'stable' does not match severity counts"):
        drill.evaluate_incident("database_failure", result)


def test_fetch_incident_retries_a_transient_reset_before_fetch(monkeypatch):
    drill = load_drill_module()
    attempts = {"fetch": 0}

    def get_json(url):
        if url.endswith("/health"):
            return {"status": "healthy"}
        if url.endswith("/scenarios"):
            return {"available_scenarios": {"database_failure": {}}}
        attempts["fetch"] += 1
        if attempts["fetch"] == 1:
            raise drill.TransientIncidentDrillError("connection reset")
        return database_result()

    monkeypatch.setattr(drill, "_get_json", get_json)
    monkeypatch.setattr(drill.time, "sleep", lambda _: None)

    result = drill.fetch_incident("http://api", "database_failure", attempts=2)

    assert result == database_result()
    assert attempts["fetch"] == 2
