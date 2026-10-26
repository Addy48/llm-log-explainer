import os
import time
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

import llm
from analyzer import analyze_incident, analyze_log, parse_text


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        process_time = time.time() - start
        response.headers["X-Process-Time-Ms"] = f"{process_time * 1000:.2f}"
        return response


LOG_GENERATOR_URL = os.getenv("LOG_GENERATOR_URL", "http://log-generator:5000")

app = FastAPI(title="LLM Log Explainer", version="2.0.0")
app.add_middleware(TimingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time-Ms"],
)


class LogEntry(BaseModel):
    timestamp: str = ""
    level: str
    message: str
    context: dict = Field(default_factory=dict)
    request_id: Optional[str] = None


class ExplainBatchRequest(BaseModel):
    logs: list[LogEntry]
    scenario: Optional[str] = None


class AnalyzeTextRequest(BaseModel):
    text: str = Field(max_length=200_000)


class IncidentRequest(BaseModel):
    logs: list[LogEntry] = Field(max_length=300)
    scenario: Optional[str] = None


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "llm-service",
        "engine": "rules",
        "llm_available": llm.available(),
        "llm_model": llm.MODEL if llm.available() else None,
    }


@app.post("/explain")
def explain(log: LogEntry):
    data = log.model_dump()
    return {"log": data, "explanation": analyze_log(data)}


def _batch(logs: list[dict], scenario: Optional[str] = None) -> dict:
    analyses = [analyze_log(l) for l in logs]
    incident = analyze_incident(logs, analyses, scenario)
    return {
        "count": len(logs),
        "explanations": [{"log": l, "explanation": a} for l, a in zip(logs, analyses)],
        "incident": incident,
        # kept for older clients of the v1 contract
        "root_cause": incident.get("root_cause"),
        "recommended_actions": incident.get("recommended_actions", []),
    }


@app.post("/explain-batch")
def explain_batch(request: ExplainBatchRequest):
    return _batch([l.model_dump() for l in request.logs], request.scenario)


@app.post("/analyze-text")
def analyze_text(request: AnalyzeTextRequest):
    logs = parse_text(request.text)
    if not logs:
        raise HTTPException(400, "No log lines found in the pasted text")
    return _batch(logs)


@app.get("/scenarios")
def scenarios():
    try:
        return requests.get(f"{LOG_GENERATOR_URL}/scenario", timeout=5).json()
    except requests.RequestException as e:
        raise HTTPException(503, f"Log generator unavailable: {e}")


@app.get("/fetch-and-explain")
def fetch_and_explain(scenario: Optional[str] = None, count: int = 1):
    if scenario:
        url = f"{LOG_GENERATOR_URL}/scenario/{scenario}"
    elif count > 1:
        url = f"{LOG_GENERATOR_URL}/generate/batch?count={min(count, 50)}"
    else:
        url = f"{LOG_GENERATOR_URL}/generate"
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(503, f"Log generator unavailable: {e}")
    if resp.status_code == 404:
        raise HTTPException(404, resp.json().get("error", "Unknown scenario"))
    data = resp.json()
    if "logs" in data:
        return _batch(data["logs"], scenario)
    return explain(LogEntry(**data))


@app.post("/explain-incident-llm")
def explain_incident_llm(request: IncidentRequest):
    if not llm.available():
        raise HTTPException(503, "LLM is not configured. Set GROQ_API_KEY in .env to enable LLM explanations.")
    logs = [l.model_dump() for l in request.logs]
    analyses = [analyze_log(l) for l in logs]
    incident = analyze_incident(logs, analyses, request.scenario)
    try:
        result = llm.explain_incident(logs, analyses, incident)
    except llm.LLMError as e:
        raise HTTPException(e.status, str(e))
    if result is None:
        raise HTTPException(422, "LLM returned an unreadable answer; showing the rule-based result instead")
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
