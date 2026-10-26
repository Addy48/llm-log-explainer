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
    assert assessment["diagnosis_method"] == "log-based inference; no scenario hint passed to analyzer"


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


def test_fetch_incident_posts_scenario_logs_without_scenario_hint(monkeypatch):
    drill = load_drill_module()
    generated_logs = [{"level": "ERROR", "message": "Database connection timeout"}]
    posted = {}

    def get_json(url):
        if url == "http://api/health":
            return {"status": "healthy"}
        if url == "http://api/scenarios":
            return {"available_scenarios": {"database_failure": "Database outage"}}
        if url == "http://generator/scenario/database_failure":
            return {"logs": generated_logs, "log_count": 1, "scenario": "database_failure"}
        raise AssertionError(f"unexpected GET {url}")

    def post_json(url, payload, attempts, interval):
        posted["url"] = url
        posted["payload"] = payload
        return database_result()

    monkeypatch.setattr(drill, "_get_json", get_json)
    monkeypatch.setattr(drill, "_post_json_with_retry", post_json)

    result = drill.fetch_incident(
        "http://api", "database_failure", generator_url="http://generator", attempts=1
    )

    assert result == database_result()
    assert posted == {
        "url": "http://api/explain-batch",
        "payload": {"logs": generated_logs},
    }


def test_fetch_incident_retries_transient_generator_read(monkeypatch):
    drill = load_drill_module()
    generated_logs = [{"level": "ERROR", "message": "Database connection timeout"}]
    generator_reads = {"count": 0}

    def get_json(url):
        if url == "http://api/health":
            return {"status": "healthy"}
        if url == "http://api/scenarios":
            return {"available_scenarios": {"database_failure": "Database outage"}}
        if url == "http://generator/scenario/database_failure":
            generator_reads["count"] += 1
            if generator_reads["count"] == 1:
                raise drill.TransientIncidentDrillError("connection reset")
            return {"logs": generated_logs, "log_count": 1, "scenario": "database_failure"}
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr(drill, "_get_json", get_json)
    monkeypatch.setattr(drill, "_post_json_with_retry", lambda *args: database_result())
    monkeypatch.setattr(drill.time, "sleep", lambda _: None)

    drill.fetch_incident(
        "http://api", "database_failure", attempts=2, generator_url="http://generator"
    )

    assert generator_reads["count"] == 2
