"""Optional LLM-written incident explanation (Groq, OpenAI-compatible API).

Enabled when GROQ_API_KEY is set. The rule-based analyzer stays the default and
the fallback, so the app works fully offline.
"""
import json
import os
from typing import Optional

import requests

from prompts import LLM_SYSTEM_PROMPT

API_URL = os.getenv("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

RESPONSE_SHAPE = """Reply with one JSON object only, with these keys:
{"title": short incident title (under 8 words),
 "summary": three or four plain-language sentences,
 "root_cause": one sentence,
 "severity": "HIGH" | "MEDIUM" | "LOW",
 "recommended_actions": [up to four short imperative steps],
 "key_lines": [indexes of the log lines that matter most]}"""


class LLMError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def available() -> bool:
    return bool(os.getenv("GROQ_API_KEY")) and os.getenv("LLM_DISABLED") != "1"


def explain_incident(logs: list, analyses: list, incident: dict) -> Optional[dict]:
    lines = "\n".join(
        f"[{i}] {l.get('timestamp', '')} {l.get('level', '')} {l.get('message', '')}"
        f"  (rules: {a['severity']}/{a['category']})"
        for i, (l, a) in enumerate(zip(logs, analyses))
    )
    pre = json.dumps({k: incident.get(k) for k in ("category", "status", "severity_counts", "root_cause")})
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": f"{LLM_SYSTEM_PROMPT}\n\n{RESPONSE_SHAPE}"},
                    {"role": "user", "content": f"Pre-classifier: {pre}\n\nLogs:\n{lines}"},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "max_tokens": 1500,
            },
            timeout=45,
        )
    except requests.RequestException as e:
        raise LLMError(502, f"LLM request failed: {e}")
    if resp.status_code == 401:
        raise LLMError(401, "LLM API key was rejected")
    if resp.status_code == 429:
        raise LLMError(429, "LLM rate limit hit, try again shortly")
    if not resp.ok:
        raise LLMError(502, f"LLM returned {resp.status_code}")

    body = resp.json()
    try:
        result = json.loads(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, json.JSONDecodeError):
        return None
    result["recommended_actions"] = [str(a) for a in result.get("recommended_actions", [])][:4]
    result["key_lines"] = [i for i in result.get("key_lines", []) if isinstance(i, int) and 0 <= i < len(logs)]
    result["engine"] = "llm"
    result["model"] = body.get("model", MODEL)
    return result
