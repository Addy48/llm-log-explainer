"""Rule-based log analyzer.

Classifies each log line into a failure category and a severity, and keeps the
evidence (matched terms) so every result can be traced back to the text that
produced it. Confidence is derived from how strongly the top category wins over
the others, not invented.
"""
import json
import re
from collections import Counter
from datetime import datetime
from typing import Optional

from prompts import CATEGORY_PLAYBOOK, SCENARIO_PATTERNS

# category -> {term: weight}. Terms are matched as lowercase substrings.
CATEGORY_SIGNALS = {
    "database": {
        "database": 3, "postgres": 3, "db.": 2, "query": 2, "deadlock": 3,
        "transaction": 2, "migration": 1, "connection pool": 2, "connection attempt": 2,
        "replica": 2, "sql": 2, "select ": 1,
    },
    "security": {
        "login": 2, "auth": 2, "credential": 3, "password": 3, "brute force": 4,
        "account locked": 4, "security": 3, "block list": 3, "unauthorized": 4,
        "ssl certificate": 3, "token": 1, "anomaly": 1,
    },
    "memory": {
        "memory": 3, "heap": 3, "outofmemory": 4, "garbage collection": 2, "gc": 1,
        "leak": 4, "ram": 2, "heapdump": 2, "oom": 3,
    },
    "traffic": {
        "rate limit": 4, "429": 3, "requests/minute": 2, "latency": 2, "queue depth": 3,
        "auto-scaling": 3, "scaling": 2, "load balanc": 2, "504": 3, "gateway": 2,
        "too many requests": 3, "pending requests": 2, "instance": 1,
    },
    "storage": {
        "disk": 4, "sector": 3, "smart": 3, "i/o": 3, "write latency": 3, "/dev/": 2,
        "filesystem": 3, "volume": 2, "log rotation": 2, "capacity": 1,
    },
    "cache": {
        "redis": 4, "cache": 3, "ttl": 3, "thundering herd": 4, "stampede": 4,
        "xfetch": 2, "lock": 1,
    },
    "config": {
        "config": 3, ".yaml": 3, "filenotfound": 3, "environment variable": 2,
        "deprecated": 2, "not found": 1,
    },
    "network": {
        "connection refused": 4, "timed out": 2, "timeout": 2, "unreachable": 3,
        "network": 3, "dns": 3, "socket": 2, "retry": 1,
    },
}

ESCALATORS = {
    "crash": 3, "failed after": 3, "exhausted": 3, "exceeded": 2, "critical": 3,
    "unavailable": 3, "i/o error": 3, "locked": 2, "brute force": 3, "breach": 4,
    "fatal": 4, "panic": 4, "corrupt": 3, "emergency": 3, "deadlock": 2,
    "outofmemory": 3, "refused": 2, "failed": 1, "degraded": 1, "replacement": 2,
    "timeout": 2, "thundering herd": 2, "504": 2,
}

CALMERS = {
    "successful": 2, "completed": 2, "normalized": 2, "online": 1, "started": 1,
    "initialized": 1, "refreshed": 1, "established": 1, "reloaded": 1, "processed in": 2,
}

LEVEL_BASE = {"CRITICAL": 5, "FATAL": 5, "ERROR": 4, "WARNING": 2, "WARN": 2, "INFO": 0, "DEBUG": 0}

LEVEL_ALIASES = {"WARN": "WARNING", "ERR": "ERROR", "FATAL": "CRITICAL", "CRIT": "CRITICAL"}

SCENARIO_CATEGORY = {
    "database_failure": "database",
    "auth_breach": "security",
    "memory_leak": "memory",
    "api_overload": "traffic",
    "disk_failure": "storage",
    "redis_cache_stampede": "cache",
}


def _normalize_level(level: Optional[str]) -> str:
    lvl = (level or "INFO").strip().upper()
    return LEVEL_ALIASES.get(lvl, lvl)


_PATTERNS = {}


def _pattern(term: str):
    # Terms must start on a word boundary ("i/o" must not match "/api/orders").
    # Short terms must also end on one ("gc" must not match "gcp").
    if term not in _PATTERNS:
        left = r"(?<![a-z0-9])" if term[0].isalnum() else ""
        right = r"(?![a-z0-9])" if len(term) <= 4 and term[-1].isalnum() else ""
        _PATTERNS[term] = re.compile(left + re.escape(term) + right)
    return _PATTERNS[term]


def _match(text: str, table: dict) -> list:
    return [(term, w) for term, w in table.items() if _pattern(term).search(text)]


def analyze_log(log: dict) -> dict:
    """Analyze one log dict ({level, message, timestamp?, context?})."""
    level = _normalize_level(log.get("level"))
    message = log.get("message") or ""
    module = (log.get("context") or {}).get("module") or log.get("module") or ""
    text = f"{message} {module}".lower()

    scores = {}
    evidence = {}
    for category, table in CATEGORY_SIGNALS.items():
        hits = _match(text, table)
        if hits:
            scores[category] = sum(w for _, w in hits)
            evidence[category] = [t for t, _ in hits]

    if scores:
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        category, top = ranked[0]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        # Margin of the winner over the runner-up, plus a bonus for total signal strength.
        margin = (top - runner_up) / top
        strength = min(top, 8) / 8
        confidence = round(0.45 + 0.35 * margin + 0.2 * strength, 2)
    else:
        category, confidence = "general", 0.35

    escalation = _match(text, ESCALATORS)
    calming = _match(text, CALMERS)
    risk = LEVEL_BASE.get(level, 0) + sum(w for _, w in escalation) - sum(w for _, w in calming)
    if risk >= 6:
        severity = "HIGH"
    elif risk >= 2:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    playbook = CATEGORY_PLAYBOOK[category]
    signals = evidence.get(category, []) + [t for t, _ in escalation]
    return {
        "category": category,
        "category_label": playbook["label"],
        "severity": severity,
        "risk_score": max(risk, 0),
        "confidence": confidence,
        "signals": sorted(set(signals)),
        "explanation": _explain(level, module, playbook, severity),
        "suggestion": playbook["actions"][0] if severity != "LOW" else playbook["low_action"],
        "engine": "rules",
    }


def _explain(level: str, module: str, playbook: dict, severity: str) -> str:
    source = f" from {module}" if module else ""
    if severity == "LOW":
        return f"{level.title()} event{source}. {playbook['low_note']}"
    return f"{level.title()}{source}: {playbook['summary']}"


def analyze_incident(logs: list, analyses: list, scenario: Optional[str] = None) -> dict:
    """Aggregate per-line results into one incident summary."""
    if not logs:
        return {}
    sev = Counter(a["severity"] for a in analyses)
    weighted = Counter()
    for a in analyses:
        if a["category"] != "general":
            weighted[a["category"]] += {"HIGH": 3, "MEDIUM": 2, "LOW": 1}[a["severity"]]

    category = SCENARIO_CATEGORY.get(scenario or "") or (weighted.most_common(1)[0][0] if weighted else "general")
    playbook = CATEGORY_PLAYBOOK[category]
    pattern = SCENARIO_PATTERNS.get(scenario or "")

    def first(pred):
        return next((i for i, a in enumerate(analyses) if pred(a)), None)

    first_warn = first(lambda a: a["severity"] in ("MEDIUM", "HIGH"))
    first_high = first(lambda a: a["severity"] == "HIGH")
    timeline = []
    if first_warn is not None:
        timeline.append({"index": first_warn, "label": "First warning sign", "message": logs[first_warn].get("message")})
    if first_high is not None:
        timeline.append({"index": first_high, "label": "Became critical", "message": logs[first_high].get("message")})
    last_high = max((i for i, a in enumerate(analyses) if a["severity"] == "HIGH"), default=None)
    if last_high is not None and last_high + 1 < len(logs):
        timeline.append({"index": last_high + 1, "label": "Response / recovery", "message": logs[last_high + 1].get("message")})

    duration = _duration_seconds(logs)
    health = max(0, 100 - 18 * sev["HIGH"] - 6 * sev["MEDIUM"])
    status = "critical" if sev["HIGH"] >= 2 else "degraded" if sev["HIGH"] or sev["MEDIUM"] >= 3 else "stable"

    return {
        "scenario": scenario,
        "category": category,
        "category_label": playbook["label"],
        "status": status,
        "health_score": health,
        "severity_counts": {"HIGH": sev["HIGH"], "MEDIUM": sev["MEDIUM"], "LOW": sev["LOW"]},
        "duration_seconds": duration,
        "root_cause": pattern["root_cause"] if pattern else playbook["root_cause"],
        "recommended_actions": pattern["actions"] if pattern else playbook["actions"],
        "timeline": timeline,
        "summary": _incident_sentence(len(logs), sev, playbook, duration),
        "engine": "rules",
    }


def _incident_sentence(n, sev, playbook, duration):
    span = f" over {duration:.0f}s" if duration else ""
    return (f"{n} lines{span}: {sev['HIGH']} high, {sev['MEDIUM']} medium, {sev['LOW']} low severity. "
            f"Dominant pattern: {playbook['label'].lower()}.")


def _duration_seconds(logs):
    stamps = []
    for log in logs:
        try:
            ts = datetime.fromisoformat(str(log.get("timestamp", "")).replace("Z", "+00:00"))
            stamps.append(ts.replace(tzinfo=None))
        except ValueError:
            pass
    if len(stamps) < 2:
        return None
    return (max(stamps) - min(stamps)).total_seconds()


# ── Raw text parsing ───────────────────────────────────────────────────────

_LEVELS = r"(CRITICAL|FATAL|ERROR|ERR|WARNING|WARN|INFO|DEBUG|CRIT)"
_ISO = re.compile(rf"^\s*(\d{{4}}-\d{{2}}-\d{{2}}[T ][\d:.,]+(?:Z|[+-]\d{{2}}:?\d{{2}})?)\s+\[?{_LEVELS}\]?\s*[:\-]?\s*(.*)$", re.I)
_BRACKET = re.compile(rf"^\s*\[?{_LEVELS}\]?\s*[:\-]?\s+(.*)$", re.I)
_HDFS = re.compile(rf"^\s*(\d{{6}})\s+(\d{{6}})\s+\d+\s+{_LEVELS}\s+([\w.$]+):\s*(.*)$", re.I)
_ANYLEVEL = re.compile(rf"\b{_LEVELS}\b")


def parse_line(line: str) -> Optional[dict]:
    """Turn one raw log line (JSON, ISO-timestamped, [LEVEL], or HDFS) into a log dict."""
    line = line.strip()
    if not line:
        return None
    if line.startswith("{"):
        try:
            obj = json.loads(line)
            return {
                "timestamp": str(obj.get("timestamp") or obj.get("time") or ""),
                "level": _normalize_level(obj.get("level") or obj.get("severity")),
                "message": str(obj.get("message") or obj.get("msg") or line),
                "context": {"module": obj.get("module") or obj.get("logger") or ""},
            }
        except json.JSONDecodeError:
            pass
    m = _HDFS.match(line)
    if m:
        d, t, lvl, mod, msg = m.groups()
        ts = f"20{d[:2]}-{d[2:4]}-{d[4:]}T{t[:2]}:{t[2:4]}:{t[4:]}"
        return {"timestamp": ts, "level": _normalize_level(lvl), "message": msg, "context": {"module": mod}}
    m = _ISO.match(line)
    if m:
        ts, lvl, msg = m.groups()
        return {"timestamp": ts.replace(" ", "T", 1), "level": _normalize_level(lvl), "message": msg, "context": {}}
    m = _BRACKET.match(line)
    if m:
        lvl, msg = m.groups()
        return {"timestamp": "", "level": _normalize_level(lvl), "message": msg, "context": {}}
    m = _ANYLEVEL.search(line)
    return {"timestamp": "", "level": _normalize_level(m.group(1) if m else "INFO"), "message": line, "context": {}}


def parse_text(text: str, limit: int = 500) -> list:
    logs = [p for p in (parse_line(l) for l in text.splitlines()) if p]
    return logs[:limit]
