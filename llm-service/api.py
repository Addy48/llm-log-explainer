import os
import json
import torch
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Optional
from typing import List
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification
from prompts import EXPLANATION_TEMPLATES, SCENARIO_PATTERNS

app = FastAPI(title="LLM Log Explainer Service", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_GENERATOR_URL = os.environ.get("LOG_GENERATOR_URL", "http://localhost:5000")
MODEL_DIR = os.environ.get("MODEL_DIR", "./models/distilbert-log")

print(f"Loading model from {MODEL_DIR}...")
try:
    tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_DIR)
    model = DistilBertForSequenceClassification.from_pretrained(MODEL_DIR)
    model.eval()
    with open(os.path.join(MODEL_DIR, "label_map.json")) as f:
        label_map = {str(k): v for k, v in json.load(f).items()}
    print(f"Model loaded. Labels: {label_map}")
except Exception as e:
    print(f"Model load error: {e}")
    label_map = {"0": "LOW", "1": "MEDIUM", "2": "HIGH"}

class LogContext(BaseModel):
    module: str
    line: int
    process_id: int
    thread_id: Optional[str] = None

class LogEntry(BaseModel):
    id: str
    request_id: Optional[str] = None
    timestamp: str
    level: str
    message: str
    context: LogContext

class LogExplanation(BaseModel):
    log_id: str
    explanation: str
    severity: str
    suggestion: str

class ExplainBatchRequest(BaseModel):
    logs: List[LogEntry]
    scenario: Optional[str] = None

def classify(message: str) -> str:
    inputs = tokenizer(message, truncation=True, padding=True, max_length=128, return_tensors="pt")
    with torch.no_grad():
        pred_id = torch.argmax(model(**inputs).logits, dim=1).item()
    return label_map.get(str(pred_id), "LOW")

def explain(log: LogEntry) -> LogExplanation:
    severity = classify(log.message)
    t = EXPLANATION_TEMPLATES.get(severity, EXPLANATION_TEMPLATES['LOW'])
    return LogExplanation(
        log_id=log.id,
        explanation=f"{t['prefix']} The {log.context.module} module reported: \"{log.message}\". Logged at {log.level} level on {log.timestamp}.",
        severity=severity.lower(),
        suggestion=t['action'],
    )

@app.get("/health")
def health():
    return {"status": "healthy", "service": "llm-service", "model": "distilbert-log", "labels": list(label_map.values())}

@app.post("/explain", response_model=LogExplanation)
def explain_single(log: LogEntry):
    try:
        return explain(log)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/explain/batch")
def explain_batch(req: ExplainBatchRequest):
    try:
        explanations = [explain(log) for log in req.logs]
        if req.scenario and req.scenario in SCENARIO_PATTERNS:
            p = SCENARIO_PATTERNS[req.scenario]
            high = sum(1 for e in explanations if e.severity == "high")
            med = sum(1 for e in explanations if e.severity == "medium")
            return {
                "scenario": req.scenario,
                "summary": f"Analysed {len(explanations)} logs for '{req.scenario}'. {high} critical, {med} warnings. {p['root_cause']}",
                "log_explanations": explanations,
                "root_cause": p['root_cause'],
                "recommended_actions": p['actions'],
            }
        return {"count": len(explanations), "explanations": explanations}
    except Exception as e:
        raise HTTPException(500, str(e))

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
