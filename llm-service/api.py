from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import os
from pydantic import BaseModel
from typing import Optional

LOG_GENERATOR_URL = os.getenv("LOG_GENERATOR_URL", "http://log-generator:5000")
MODEL_DIR = os.getenv("MODEL_DIR", "./models/distilbert-log")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str

class ExplainBatchRequest(BaseModel):
    logs: list
    scenario: Optional[str] = None

from prompts import EXPLANATION_TEMPLATES as EXPLANATIONS


@app.get("/health")
def health():
    return {"status": "healthy", "service": "llm-service"}

@app.post("/explain")
def explain(log: LogEntry):
    return {
        "log": log.dict(),
        "explanation": EXPLANATIONS.get("database_failure", {})
    }

@app.post("/explain-batch")
def explain_batch(request: ExplainBatchRequest):
    explanations = []
    for log in request.logs:
        p = EXPLANATIONS.get(request.scenario or "database_failure", {})
        explanations.append({
            "log": log if isinstance(log, dict) else log.dict(),
            "root_cause": p.get("root_cause", "Unknown"),
            "recommended_actions": p.get("actions", []),
        })
    return {"count": len(explanations), "explanations": explanations}

@app.get("/fetch-and-explain")
def fetch_and_explain(scenario: Optional[str] = None):
    try:
        url = f"{LOG_GENERATOR_URL}/scenario/{scenario}" if scenario else f"{LOG_GENERATOR_URL}/generate"
        data = requests.get(url, timeout=10).json()
    except Exception as e:
        raise HTTPException(503, f"Log generator unavailable: {e}")
    if "logs" in data:
        return explain_batch(ExplainBatchRequest(logs=[LogEntry(**l) for l in data["logs"]], scenario=scenario))
    return explain(LogEntry(**data))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
