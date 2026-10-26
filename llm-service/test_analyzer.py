"""Check the analyzer picks the right category for every generator scenario."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "log-generator"))

from app import generate_scenario_logs, SCENARIOS  # noqa: E402
from analyzer import SCENARIO_CATEGORY, analyze_incident, analyze_log  # noqa: E402


def test_every_scenario_detected_without_hint():
    for name in SCENARIOS:
        logs = generate_scenario_logs(name)
        analyses = [analyze_log(l) for l in logs]
        incident = analyze_incident(logs, analyses)  # no scenario hint
        assert incident["category"] == SCENARIO_CATEGORY[name], name
        assert incident["severity_counts"]["HIGH"] >= 1, name
