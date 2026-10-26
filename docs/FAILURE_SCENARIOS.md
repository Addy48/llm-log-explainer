# Failure Scenarios and Log Taxonomy

The Flask `log-generator` service emits ordinary sample logs and six correlated failure sequences. A scenario shares one request ID across its lines and uses increasing timestamps to make the dashboard timeline readable. The sequence is synthetic and educational; it does not cause a real database, identity, memory, traffic, cache, or disk failure.

## Architecture

1. `log-generator` (Flask) creates random logs and named incident sequences.
2. `llm-service` (FastAPI) requests those logs, classifies each line with `analyzer.py`, aggregates an incident, and optionally calls Groq for a narrative.
3. `web-interface` serves the dashboard. Its browser code calls the API directly.

The live API uses deterministic weighted rules. DistilBERT training and evaluation are a separate experiment; the live API does not load those weights.

## Scenario catalog

| Scenario name | Expected category | Simulated sequence |
|---|---|---|
| `database_failure` | `database` | Connection timeouts and retry activity, followed by a read-only/cache fallback |
| `auth_breach` | `security` | Repeated login failures, account lockout, and security response |
| `memory_leak` | `memory` | Heap growth, failed garbage collection, memory exhaustion, and crash response |
| `api_overload` | `traffic` | Rate limits, queue/latency pressure, and scaling response |
| `disk_failure` | `storage` | Disk/sector warnings, failed writes, and volume failover |
| `redis_cache_stampede` | `cache` | Cache TTL expiry, a burst of misses, and a thundering herd on the backing store |

## Log classification

- **Category:** weighted keyword signals in the log message and module select the strongest category. Matched signal words are returned with each analysis. When no category signal matches, the category is `general`.
- **Severity:** log-level base risk plus escalation-word weights minus calming-word weights. Risk `>= 6` is `HIGH`; `>= 2` is `MEDIUM`; otherwise `LOW`.
- **Confidence:** derived from the winning category's margin over the runner-up and total signal strength. A log without category signals receives `0.35` confidence.
- **Incident category:** named scenarios use their known scenario-to-category mapping; unspecific batches use the severity-weighted category counts.
- **Health:** `max(0, 100 - 18 × HIGH_count - 6 × MEDIUM_count)`.
- **Status:** `critical` for at least two HIGH lines; `degraded` for one HIGH or at least three MEDIUM lines; otherwise `stable`.

These values are transparent demo heuristics, not a calibrated production risk score.

## Generate a scenario

With Docker Compose running:

```bash
curl -sS http://localhost:5001/scenario
curl -sS http://localhost:5001/scenario/database_failure
curl -sS "http://localhost:8000/fetch-and-explain?scenario=database_failure"
```

The first two requests call the generator directly. The third goes through the API, which fetches the sequence from the generator and returns per-line results plus an incident summary.
