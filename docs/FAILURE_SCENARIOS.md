# Failure Scenarios & Log Taxonomy

## Architecture Overview
The system coordinates three services:
1. `log-generator` (Flask): Produces correlated anomaly sequences and normal telemetry.
2. `llm-service` (FastAPI): a rule-based analyzer for live requests, incident aggregation, and optional Groq-written explanations. DistilBERT training/evaluation is a separate experiment and is not used by the live API.
3. `web-interface`: static HTML/CSS/JavaScript dashboard served by `http-server` in its container.

## Supported Incident Scenarios
- **Database Failure**: Database connection timeouts and retries, followed by a read-only cache fallback.
- **Auth Breach**: Rapid brute-force login attempts, firewall IP bans, admin notifications.
- **Memory Leak**: JVM/Process heap trending upward, failed GC recovery, crash dumps.
- **API Overload**: Rate limit 429 warnings, auto-scaling instance provisioning.
- **Redis Cache Stampede**: TTL expiration under concurrent load, thundering herd mitigation.
- **Disk Failure**: Sector read errors, file write I/O failures, volume failovers.
