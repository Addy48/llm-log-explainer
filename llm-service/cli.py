"""CLI utility for LLM log explanation from files or stdin."""
import argparse
import sys
import json
from prompts import EXPLANATION_TEMPLATES

def main():
    parser = argparse.ArgumentParser(description="LLM Log Explainer CLI")
    parser.add_argument("file", nargs="?", type=argparse.FileType("r"), default=sys.stdin,
                        help="Input log file (defaults to stdin)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    lines = [line.strip() for line in args.file if line.strip()]
    print(f"Loaded {len(lines)} log lines for analysis...", file=sys.stderr)

    results = []
    for line in lines:
        matched = "database_failure"
        if "Redis" in line or "cache" in line.lower():
            matched = "redis_cache_stampede"
        elif "disk" in line.lower() or "io" in line.lower():
            matched = "disk_failure"
        elif "memory" in line.lower() or "heap" in line.lower():
            matched = "memory_leak"

        tmpl = EXPLANATION_TEMPLATES.get(matched, {})
        results.append({
            "raw_log": line,
            "category": matched,
            "root_cause": tmpl.get("root_cause", "Anomaly detected"),
            "actions": tmpl.get("actions", [])
        })

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"[{r['category'].upper()}] {r['raw_log']}")
            print(f"  Root Cause: {r['root_cause']}")
            for act in r['actions']:
                print(f"  -> {act}")
            print()

if __name__ == "__main__":
    main()
