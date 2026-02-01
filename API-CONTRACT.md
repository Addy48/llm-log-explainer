# API Contract

## Log Format
```json
{
  "timestamp": "2026-02-01T10:30:00Z",
  "level": "ERROR|WARNING|INFO",
  "message": "Connection timeout to database",
  "context": {"module": "db_handler", "line": 45}
}
```

## Explanation Format
```json
{
  "log_id": "uuid",
  "explanation": "Plain English explanation",
  "severity": "high|medium|low",
  "suggestion": "Recommended action"
}
```
