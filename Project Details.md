# Project Details — Current Reference

This page points to the current, implemented project. The original March 2026 build proposal has been preserved as a [historical plan](docs/archive/PROJECT-PLAN-2026-03.md); it is not a current runbook.

## Current project

LLM Log Explainer is a three-service AIOps demo:

- **`log-generator`** — Flask service that emits random logs and six correlated failure scenarios.
- **`llm-service`** — FastAPI service that uses a deterministic, weighted-rule analyzer to classify logs and aggregate incidents. A Groq API call can optionally add a narrative explanation.
- **`web-interface`** — static dashboard served on port `3000`; browser JavaScript calls the API on port `8000`.

The DistilBERT code and weights are an optional training/evaluation experiment. The live API does not load the model.

## Current workflow

- Docker Compose builds and runs all three services on the `llm-network` bridge network.
- Healthchecks report generator/API readiness; `condition: service_healthy` gates dependent startup.
- GitHub Actions runs tests, builds the stack, sends a selectable incident through the API, validates the diagnosis, uploads a JSON artifact, and shuts down the runner's containers.
- The Actions incident drill does not publish images or deploy to a cloud account.

## Start and verify

```bash
# Docker Desktop / Engine running

docker compose up -d --build
# dashboard: http://localhost:3000
# API docs:  http://localhost:8000/docs

# Alternative without Docker
./run_local.sh

# Tests
.venv/bin/python -m pytest -p no:cacheprovider llm-service log-generator scripts
```

Stop a Compose run with `docker compose down`; stop `run_local.sh` with `Ctrl+C`.

## Current documentation

- [README](README.md) — architecture diagrams, quick starts, API examples, cloud mapping, limitations, and troubleshooting.
- [API contract](API-CONTRACT.md) — routes, request/response shapes, and status codes.
- [Failure scenarios](docs/FAILURE_SCENARIOS.md) — generated scenario taxonomy and scoring rules.
- [Incident drill](docs/INCIDENT-DRILL.md) — GitHub Actions behavior and local drill commands.
