# Failure Scenarios & Log Taxonomy

## Architecture Overview
The system coordinates three autonomous microservices:
1. `log-generator` (Flask): Produces correlated anomaly sequences and normal telemetry.
2. `llm-service` (FastAPI): DistilBERT classification + template/LLM explanations.
3. `web-interface` (Nginx): Real-time operations dashboard.

## Supported Incident Scenarios
- **Database Failure**: Connection pool exhaustion, network timeouts, read-only cache fallback.
- **Auth Breach**: Rapid brute-force login attempts, firewall IP bans, admin notifications.
- **Memory Leak**: JVM/Process heap trending upward, failed GC recovery, crash dumps.
- **API Overload**: Rate limit 429 warnings, auto-scaling instance provisioning.
- **Redis Cache Stampede**: TTL expiration under concurrent load, thundering herd mitigation.
- **Disk Failure**: Sector read errors, file write I/O failures, volume failovers.
