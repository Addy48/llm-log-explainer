#!/usr/bin/env python3
"""Run a project failure scenario through the live Compose stack and report the gate."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


SCENARIO_CATEGORIES = {
    "database_failure": "database",
    "auth_breach": "security",
    "memory_leak": "memory",
    "api_overload": "traffic",
    "disk_failure": "storage",
    "redis_cache_stampede": "cache",
}


class IncidentDrillError(RuntimeError):
    """The incident drill could not produce or validate an expected diagnosis."""


class TransientIncidentDrillError(IncidentDrillError):
    """A temporary API/network condition that can succeed on retry."""


def evaluate_incident(scenario: str, result: dict) -> dict:
    """Validate an API result and turn its incident status into a simulated gate."""
    if scenario not in SCENARIO_CATEGORIES:
        raise IncidentDrillError(f"unsupported scenario: {scenario}")

    incident = result.get("incident")
    if not isinstance(incident, dict):
        raise IncidentDrillError("API response did not include an incident summary")

    expected_category = SCENARIO_CATEGORIES[scenario]
    actual_category = incident.get("category")
    if actual_category != expected_category:
        raise IncidentDrillError(
            f"expected category '{expected_category}', got '{actual_category}'"
        )

    severity_counts = incident.get("severity_counts")
    if not isinstance(severity_counts, dict):
        raise IncidentDrillError("incident summary did not include severity counts")
    for level in ("HIGH", "MEDIUM", "LOW"):
        count_at_level = severity_counts.get(level)
        if type(count_at_level) is not int or count_at_level < 0:
            raise IncidentDrillError(f"severity count for {level} must be a non-negative integer")
    high_count = severity_counts["HIGH"]
    medium_count = severity_counts["MEDIUM"]
    if high_count < 1:
        raise IncidentDrillError("expected at least one HIGH-severity log for this failure scenario")

    expected_health = max(0, 100 - 18 * high_count - 6 * medium_count)
    health_score = incident.get("health_score")
    if health_score != expected_health:
        raise IncidentDrillError(
            f"health score {health_score!r} does not match severity counts (expected {expected_health})"
        )

    expected_status = (
        "critical" if high_count >= 2
        else "degraded" if high_count or medium_count >= 3
        else "stable"
    )
    status = incident.get("status")
    if status != expected_status:
        raise IncidentDrillError(
            f"status {status!r} does not match severity counts (expected {expected_status!r})"
        )

    root_cause = incident.get("root_cause")
    actions = incident.get("recommended_actions")
    if not isinstance(root_cause, str) or not root_cause.strip():
        raise IncidentDrillError("incident summary did not include a root cause")
    if not isinstance(actions, list) or not actions:
        raise IncidentDrillError("incident summary did not include recommended actions")

    gate_decision = {
        "critical": "BLOCKED",
        "degraded": "REVIEW",
        "stable": "APPROVED",
    }[status]
    count = result.get("count")
    if not isinstance(count, int) or count < 1:
        raise IncidentDrillError("API response did not include a positive analyzed-log count")

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario,
        "expected_category": expected_category,
        "validation": "passed",
        "gate_decision": gate_decision,
        "log_count": count,
        "incident": incident,
    }


def format_report(assessment: dict) -> str:
    """Render the report used by the GitHub Actions job summary and local CLI."""
    incident = assessment["incident"]
    counts = incident["severity_counts"]
    actions = "\n".join(f"- {action}" for action in incident["recommended_actions"])
    return "\n".join(
        [
            "# AIOps Incident Drill",
            "",
            f"- **Scenario:** `{assessment['scenario']}`",
            f"- **Diagnosis check:** {assessment['validation'].upper()} "
            f"(expected `{assessment['expected_category']}`, got `{incident['category']}`)",
            f"- **Incident status:** {incident['status'].upper()}",
            f"- **Simulated release gate:** **{assessment['gate_decision']}**",
            f"- **Health score:** {incident['health_score']}/100",
            f"- **Analyzed logs:** {assessment['log_count']} "
            f"(HIGH {counts['HIGH']} · MEDIUM {counts['MEDIUM']} · LOW {counts['LOW']})",
            "",
            "## Root cause",
            "",
            incident["root_cause"],
            "",
            "## Recommended actions",
            "",
            actions,
            "",
            "> The release decision is simulated for this demo. No deployment is performed.",
            "",
        ]
    )


def _get_json(url: str) -> dict:
    try:
        with urlopen(url, timeout=5) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        error_type = TransientIncidentDrillError if error.code in (502, 503, 504) else IncidentDrillError
        raise error_type(f"API returned HTTP {error.code}: {detail}") from error
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        raise TransientIncidentDrillError(f"could not read JSON from {url}: {error}") from error


def _get_json_with_retry(url: str, attempts: int = 30, interval: float = 1.0) -> dict:
    """Retry temporary transport and gateway failures while a service settles."""
    last_error = None
    for attempt in range(attempts):
        try:
            return _get_json(url)
        except TransientIncidentDrillError as error:
            last_error = str(error)
            if attempt + 1 < attempts:
                time.sleep(interval)
    raise IncidentDrillError(f"API request failed after {attempts} attempts: {last_error}")


def fetch_incident(api_url: str, scenario: str, attempts: int = 30, interval: float = 1.0) -> dict:
    """Wait for the API and fetch one generated scenario through its real route."""
    base_url = api_url.rstrip("/")
    last_error = None
    for _ in range(attempts):
        try:
            health = _get_json(f"{base_url}/health")
            if health.get("status") == "healthy":
                catalog = _get_json(f"{base_url}/scenarios")
                available = catalog.get("available_scenarios", {})
                if scenario not in available:
                    raise IncidentDrillError(f"scenario '{scenario}' is not available from the log generator")
                break
            last_error = "API health endpoint did not report healthy"
        except IncidentDrillError as error:
            last_error = str(error)
        time.sleep(interval)
    else:
        raise IncidentDrillError(f"API did not become healthy after {attempts} attempts: {last_error}")

    query = urlencode({"scenario": scenario})
    return _get_json_with_retry(f"{base_url}/fetch-and-explain?{query}", attempts, interval)


def write_summary(markdown: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(markdown)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIO_CATEGORIES, required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report", type=Path, default=Path("incident-report.json"))
    args = parser.parse_args(argv)

    try:
        result = fetch_incident(args.api_url, args.scenario)
        assessment = evaluate_incident(args.scenario, result)
        markdown = format_report(assessment)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(assessment, indent=2) + "\n", encoding="utf-8")
        write_summary(markdown)
        print(markdown, end="")
        print(f"JSON report saved to {args.report}")
        return 0
    except (IncidentDrillError, OSError) as error:
        message = f"# AIOps Incident Drill\n\n**Validation: FAILED**\n\n{error}\n"
        write_summary(message)
        print(message, file=sys.stderr, end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
