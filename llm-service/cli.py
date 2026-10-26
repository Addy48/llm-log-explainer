"""CLI utility for log explanation from files or stdin."""
import argparse
import json
import sys

from analyzer import analyze_incident, analyze_log, parse_text


def main():
    parser = argparse.ArgumentParser(description="LLM Log Explainer CLI")
    parser.add_argument("file", nargs="?", type=argparse.FileType("r"), default=sys.stdin,
                        help="Input log file (defaults to stdin)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    logs = parse_text(args.file.read())
    print(f"Loaded {len(logs)} log lines for analysis...", file=sys.stderr)

    analyses = [analyze_log(log) for log in logs]
    incident = analyze_incident(logs, analyses)

    if args.json:
        print(json.dumps({"logs": [{"log": l, "analysis": a} for l, a in zip(logs, analyses)],
                          "incident": incident}, indent=2))
        return

    for log, a in zip(logs, analyses):
        print(f"[{a['severity']:<6}] [{a['category']}] {log['message']}")
        print(f"  {a['explanation']}")
        print(f"  -> {a['suggestion']}  (confidence {a['confidence']:.0%}, signals: {', '.join(a['signals']) or 'none'})")
    if incident:
        print(f"\nIncident: {incident['status'].upper()}  health {incident['health_score']}/100")
        print(f"  Root cause: {incident['root_cause']}")
        for act in incident["recommended_actions"]:
            print(f"  -> {act}")


if __name__ == "__main__":
    main()
