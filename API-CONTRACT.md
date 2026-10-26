# API Contract

The live API is the FastAPI service on port `8000`. Open `/docs` for its generated OpenAPI schema. Log generation is provided separately by Flask on port `5001` on the host (`5000` inside Compose).

## Common log object

```json
{
  "timestamp": "2026-10-26T10:30:00Z",
  "level": "ERROR",
  "message": "Database connection failed after retries",
  "context": {"module": "db_handler", "line": 45},
  "request_id": "req_example"
}
```

`level` and `message` are required by the API model. `timestamp`, `context`, and `request_id` are optional. The analyzer accepts common level aliases such as `WARN`, `ERR`, and `FATAL`.

## `GET /health`

Reports API readiness and whether the optional LLM is configured.

```json
{
  "status": "healthy",
  "service": "llm-service",
  "engine": "rules",
  "llm_available": false,
  "llm_model": null
}
```

## `POST /explain`

Analyze one log line.

**Request:** one common log object.

**Response:**

```json
{
  "log": {
    "timestamp": "2026-10-26T10:30:00Z",
    "level": "ERROR",
    "message": "Database connection failed after retries",
    "context": {"module": "db_handler", "line": 45},
    "request_id": "req_example"
  },
  "explanation": {
    "category": "database",
    "category_label": "Database connectivity",
    "severity": "HIGH",
    "risk_score": 8,
    "confidence": 0.88,
    "signals": ["database", "failed", "failed after"],
    "explanation": "Error from db_handler: the service cannot reliably reach or use its database (timeouts, failed retries, lock contention).",
    "suggestion": "Check database server health and connectivity",
    "engine": "rules"
  }
}
```

The example values illustrate the shape; category label, scores, and text depend on the analyzer's rules and input.

## `POST /explain-batch`

**Request:** `{"logs": [<log>, ...], "scenario": "database_failure"}`. `scenario` is optional.

**Response:** includes `count`, an `explanations` array of `{log, explanation}` objects, and an `incident` summary. The response also includes top-level `root_cause` and `recommended_actions` for older clients.

## `POST /analyze-text`

**Request:** `{"text": "<newline-separated log lines>"}`. Text is limited to 200,000 characters. The parser recognizes JSON lines, ISO-timestamped lines, `[LEVEL]` lines, and HDFS-style lines.

**Response:** the same batch/incident shape as `/explain-batch`. Empty text (or input containing only blank lines) returns HTTP `400`. Malformed but non-empty lines are still treated as log text by the fallback parser.

## `GET /scenarios`

Returns the generator's supported scenario names and descriptions. The API proxies the generator's `/scenario` route. A generator connection failure returns HTTP `503`.

## `GET /fetch-and-explain`

Fetch logs from the generator, then analyze them.

| Query | Behavior |
|---|---|
| `scenario=<name>` | Generate and analyze a correlated scenario; returns the batch/incident shape |
| `count=<n>` | If `n > 1`, generate and analyze up to 50 random logs |
| no query | Generate and analyze one random log; returns the single-log shape |

Unknown scenario names return HTTP `404`. A generator connection failure returns HTTP `503`.

## `POST /explain-incident-llm`

Optional. Requires `GROQ_API_KEY` (and accepts an optional `scenario`). The request contains `logs` and optional `scenario`; up to 300 logs are accepted. The response includes LLM-generated `title`, `summary`, `root_cause`, `severity`, `recommended_actions`, `key_lines`, `engine`, and `model` fields. The rule-based result does not depend on this endpoint.

Provider errors are surfaced as HTTP `401` for a rejected key, `429` for a rate limit, `502` for an upstream/network error, and `503` when the LLM is not configured.

## Log-generator endpoints

| Route | Behavior |
|---|---|
| `GET /health` | Generator health and supported scenario names |
| `GET /generate` | Generate one random log |
| `GET /generate/batch?count=10` | Generate a correlated batch with a shared request ID; maximum 50 |
| `GET /generate/error`, `/generate/warning`, `/generate/info` | Generate one log at the requested level |
| `GET /scenario` | List available failure scenarios |
| `GET /scenario/<name>` | Generate a correlated scenario sequence; unknown names return HTTP `404` |

## Incident summary fields

The `incident` object returned by batch and scenario analysis contains:

- `scenario`, `category`, and `category_label`
- `status`: `critical`, `degraded`, or `stable`
- `health_score`: integer from `0` to `100`
- `severity_counts`: counts for `HIGH`, `MEDIUM`, and `LOW`
- `duration_seconds`: elapsed time from parsed timestamps, or `null`
- `root_cause`, `recommended_actions`, and `summary`
- `timeline`: selected warning, critical, and recovery line indexes/messages
- `engine`: currently `rules`

## Example requests

```bash
curl -sS http://localhost:8000/health
curl -sS "http://localhost:8000/fetch-and-explain?scenario=database_failure"
curl -sS -X POST http://localhost:8000/explain \
  -H 'Content-Type: application/json' \
  -d '{"level":"ERROR","message":"Database connection timeout"}'
curl -sS -X POST http://localhost:8000/analyze-text \
  -H 'Content-Type: application/json' \
  -d '{"text":"ERROR Database connection timeout\nWARN Retry exhausted"}'
```
