# GitHub Actions AIOps Incident Drill

This workflow connects the project's log-analysis use case to a real cloud-hosted development tool. GitHub Actions starts the same three-service Docker Compose stack used locally, injects a selected failure scenario through the existing API, checks the diagnosis, and publishes an incident report.

## What the run demonstrates

```text
GitHub Actions runner
        │
        ├── installs Python dependencies and runs project tests
        ├── validates docker-compose.yml
        ├── builds and starts the three Docker services
        ├── fetches raw logs from log-generator /scenario/<choice>
        └── posts logs to llm-service /explain-batch without a scenario hint
                    │
                    ├── log-generator creates correlated failure logs
                    └── llm-service classifies logs and aggregates an incident
                                │
                                └── Actions summary + JSON artifact
```

The drill fetches raw logs from the generator, then POSTs them to `/explain-batch` without a scenario hint. That forces the analyzer to infer a category from log content instead of echoing the selected scenario. The check passes only when the inferred category matches the expected category and the API returns a valid incident summary with at least one high-severity line, a health score, a root cause, and recommended actions. A wrong category or incomplete summary fails the workflow.

The report also shows a **simulated release decision** from the incident status:

- `critical` → `BLOCKED`
- `degraded` → `REVIEW`
- `stable` → `APPROVED`

This is an educational release-gate simulation. The repository has no deployment target, so the workflow never deploys the app. A green GitHub job means the analyzer correctly diagnosed the injected scenario; the report can still say the simulated release is blocked because that is the expected response to a critical incident.

## Run it on GitHub

The workflow runs automatically for pull requests and pushes to `main`. Once the workflow is merged into `main`, you can also choose a scenario manually:

1. Open the repository's **Actions** tab.
2. Select **AIOps Incident Drill**.
3. Choose **Run workflow** and select one of the six failure scenarios.
4. Open the run summary for the diagnosis and simulated gate decision.
5. Download `incident-report-<scenario>` from the run's artifacts for the JSON incident summary.

The scenarios are `database_failure`, `auth_breach`, `memory_leak`, `api_overload`, `disk_failure`, and `redis_cache_stampede`.

## Run the same drill locally

Start Docker Desktop, then from the repository root:

```bash
docker compose up -d --build
python scripts/incident_drill.py --scenario database_failure
# Try another scenario:
python scripts/incident_drill.py --scenario memory_leak
# If your ports differ, set the URLs explicitly:
python scripts/incident_drill.py --scenario memory_leak --api-url http://127.0.0.1:8000 --generator-url http://127.0.0.1:5001
# Stop the stack when finished:
docker compose down
```

The script writes `incident-report.json` and prints the same Markdown report that GitHub Actions adds to the job summary. The drill uses the project's rule-based analysis path and needs no Groq API key.

## Why this is more than a generic build pipeline

The workflow does not stop at “the code builds.” It exercises the actual project behavior: a failure scenario becomes generated log lines, the API analyzes those lines, and the workflow checks the incident result and demonstrates a release decision. Compose healthchecks ensure the generator and API are ready before dependents start; the drill retries brief connection resets or gateway failures while the runner settles. The same workflow also runs unit tests and builds the containers, so it combines CI with an AIOps-flavored operations check.
