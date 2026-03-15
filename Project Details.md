# Rasagya — Full Project Context (GIUE This File to Any LLM)

**Written by:** Aaditya  
**Date:** March 11, 2026  
**Repo:** https://github.com/Addy48/llm-log-explainer  
**Deadline:** ~April 10–15, 2026 (final evaluation)

---

## What Is This File?

This is everything you need to know about our project — what I've already built,
what you need to build, how the pieces connect, and what commits to make.
Feed this entire file to whatever LLM you're using (ChatGPT, Claude, anything)
and it'll have full context to help you. Don't start coding without giving your
LLM this file first.

---

## The Project in One Paragraph

We're building a 3-container Docker system for our CSE3232 lab course at MUJ.
Container 1 (mine — done) is a Flask app that generates realistic fake application
logs — database crashes, auth breaches, memory leaks, etc. Container 2 (yours) is
a FastAPI app that takes those logs, runs them through a fine-tuned DistilBERT
model you train, classifies each log as HIGH/MEDIUM/LOW severity, and returns a
plain English explanation with a recommended action. Container 3 (we build together)
is a simple web page that shows logs on the left and your explanation on the right,
side by side.

The key thing: **we are NOT using Ollama or any external API.**You need to actually fine-tune DistilBERT on real log data.
This is what makes it a real ML project instead of just an API wrapper.

---

## What I've Already Done (Don't Touch These)

### Commits on GitHub (5 total right now)

```
de1e417  Add Git LFS config and update README with DistilBERT architecture  (me)
09d5c0b  Implement Flask log generator with correlated sequences             (me)
c7ce8eb  Add Dockerfile and requirements for Flask log generator             (me)
0d93fab  Revise architecture and team member information                     (me )
f8a5683  Initialize project structure with README and API contract           (me)
```

### Files I've Built

**`log-generator/app.py`** — Flask app, fully working and tested locally.
It generates logs in this exact JSON format:
```json
{
  "id": "b45cd293-11d1-4959-aba0-43f6ceeb8516",
  "request_id": "req_b064663045bd",
  "timestamp": "2026-03-11T14:30:00.000000",
  "level": "ERROR",
  "message": "Database connection timeout after 30 seconds",
  "context": {
    "module": "db_handler",
    "line": 142,
    "process_id": 9210,
    "thread_id": "thread-1"
  }
}
```

**Endpoints your service can call:**
- `GET /health` — returns service status
- `GET /generate` — returns one random log
- `GET /generate?level=ERROR` — returns log of specific level
- `GET /generate/batch?count=10` — returns multiple logs
- `GET /scenario/database_failure` — returns 10 correlated logs telling a story
- `GET /scenario/auth_breach` — same but auth attack scenario
- `GET /scenario/memory_leak` — memory exhaustion scenario
- `GET /scenario/api_overload` — rate limiting / scaling scenario
- `GET /scenario/disk_failure` — hardware failure scenario

The scenario endpoints are the cool part — they return a sequence of logs that
build up to a failure, with shared `request_id` for correlation. Like a real
incident trace.

**`log-generator/Dockerfile`** — containerizes the Flask app on port 5000.

**`.gitattributes`** — Git LFS tracking for model files. This is critical.
When you push your trained DistilBERT weights (~250MB), GitHub will reject them
unless Git LFS is set up. I've already configured it, but you need to run
`git lfs install` on your machine once before pushing the model.

**`docker-compose.yml`** — I'm writing this soon (Commit 6). It wires all
three containers together on a shared Docker network. Once it's done, inside your
container you talk to my container using `http://log-generator:5000` not localhost.

---

## What You Need to Build (The Entire llm-service/ Folder)

Right now `llm-service/` doesn't exist in the repo at all. You're building it
from scratch. Here's every file you need and what it should do.

### Folder structure you're creating:
```
llm-service/
├── Dockerfile
├── requirements.txt
├── api.py              ← main FastAPI app
├── prompts.py          ← explanation templates
├── prepare_data.py     ← run once locally to prep training data
├── train.py            ← run on Google Colab, NOT locally
├── evaluate.py         ← run locally after training
├── data/
│   └── labeled_logs.csv
└── models/
    ├── distilbert-log/       ← Git LFS tracked
    │   ├── config.json
    │   ├── pytorch_model.bin
    │   ├── tokenizer.json
    │   └── label_map.json
    └── eval_report.txt
```

---

## Your Commits — What to Make and When

We're at 5 commits total. We need ~15+ by evaluation.
Here's your commit plan — do these in order, don't skip, don't bundle them all
into one commit (that kills the GitHub portfolio marks):

| # | Your Commit | Files | When |
|---|-------------|-------|------|
| Commit 6* | (mine — docker-compose) | docker-compose.yml | this week |
| **Commit 7** | `Add Dockerfile and requirements for LLM service` | Dockerfile, requirements.txt | Day 1|
| **Commit 8** | `Add data preparation script for Loghub dataset` | prepare_data.py | Day 4 |
| **Commit 9** | `Add labeled log dataset for DistilBERT training` | data/labeled_logs.csv | Day 7|
| **Commit 10** | `Add DistilBERT fine-tuning training script` | train.py | Day 11 |
| **Commit 11** | `Add model evaluation script` | evaluate.py | Day 14 |
| **Commit 12** | `Add trained DistilBERT model and evaluation report` | models/distilbert-log/*, eval_report.txt | Day 17 |
| **Commit 13** | `Add explanation templates and scenario patterns` | prompts.py | Day 21 |
| **Commit 14** | `Implement FastAPI endpoints with trained model` | api.py | Day 24 |

*Commit 6 is mine, so your commits are 7–14.

**Important about commit messages:** Be specific. "Add data preparation script
for Loghub dataset" is good. "update files" gets you 8/15 on portfolio marks.

---

## Step-by-Step — Build It in This Exact Order

### Step 1 — Setup (Before Anything Else)

```bash
# Install Git LFS — required before you push the model
# Mac:
brew install git-lfs
git lfs install

# Or Linux:
sudo apt install git-lfs
git lfs install

# Clone/pull the repo
git clone git@github.com:Addy48/llm-log-explainer.git
# or if already cloned:
git pull origin main
```

Create the folder structure:
```bash
mkdir -p llm-service/models/distilbert-log
mkdir -p llm-service/data
mkdir -p llm-service/raw_logs
```

Add raw_logs to .gitignore (don't commit raw Loghub files — they're big):
```bash
echo "llm-service/raw_logs/" >> .gitignore
git add .gitignore
git commit -m "Ignore raw log data from version control"
git push
```

---

### Step 2 — Commit 7: Dockerfile + requirements.txt

**What it should look like when done:**
Running `docker build -t llm-service .` inside llm-service/ should succeed
(it'll fail at runtime without the model, but the build should work).

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY models/ ./models/
COPY . .

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**requirements.txt:**
```
fastapi==0.109.0
uvicorn==0.27.0
requests==2.31.0
pydantic==2.5.0
transformers==4.38.0
torch==2.2.0
scikit-learn==1.4.0
pandas==2.2.0
```

```bash
git add llm-service/Dockerfile llm-service/requirements.txt
git commit -m "Add Dockerfile and requirements for LLM service"
git push
```

---

### Step 3 — Get Training Data

Download from here: https://github.com/logpai/loghub

Go to the `HDFS/` folder and download `HDFS_2k.log`. It's about 500KB.
Put it in `llm-service/raw_logs/HDFS_2k.log` on your machine.
Do NOT commit this file.

---

### Step 4 — Commit 8 + 9: prepare_data.py

This script reads the raw log file and creates a labeled CSV for training.
The labels are HIGH, MEDIUM, LOW based on keywords in each log line.

**Critical thing:** The script must save a `label_id` column (integer encoding
of the label) in the CSV. If it doesn't, evaluate.py will break. Use the exact
code below — don't rewrite it.

```python
"""
Run once locally to prepare training data from raw Loghub files.
Download HDFS_2k.log from: https://github.com/logpai/loghub
Place in llm-service/raw_logs/HDFS_2k.log
"""
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import os

SEVERITY_MAP = {
    'error': 'HIGH', 'fail': 'HIGH', 'exception': 'HIGH',
    'critical': 'HIGH', 'timeout': 'HIGH', 'refused': 'HIGH',
    'crash': 'HIGH', 'fatal': 'HIGH',
    'warn': 'MEDIUM', 'warning': 'MEDIUM', 'retry': 'MEDIUM',
    'slow': 'MEDIUM', 'degraded': 'MEDIUM',
    'info': 'LOW', 'success': 'LOW', 'start': 'LOW',
    'connect': 'LOW', 'completed': 'LOW', 'initialized': 'LOW',
}

def label_log(message: str) -> str:
    msg = message.lower()
    for keyword, severity in SEVERITY_MAP.items():
        if keyword in msg:
            return severity
    return 'LOW'

def prepare_dataset(log_file_path: str, output_csv: str):
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file not found: {log_file_path}")

    logs = []
    with open(log_file_path, 'r', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append({'text': line, 'label': label_log(line)})

    df = pd.DataFrame(logs)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    le = LabelEncoder()
    df['label_id'] = le.fit_transform(df['label'])

    os.makedirs(os.path.dirname(output_csv) or '.', exist_ok=True)
    df.to_csv(output_csv, index=False)

    label_map = {i: label for i, label in enumerate(le.classes_)}
    print(f"Dataset prepared: {len(df)} samples")
    print(f"Label distribution:\n{df['label'].value_counts()}")
    print(f"Label encoding: {label_map}")

if __name__ == "__main__":
    prepare_dataset("raw_logs/HDFS_2k.log", "data/labeled_logs.csv")
```

Run it:
```bash
cd llm-service
pip install pandas scikit-learn   # if not installed yet
python prepare_data.py
```

**What success looks like:** You get a `data/labeled_logs.csv` file with
columns: text, label, label_id. Print the first few rows to verify.

```bash
# Commit the script first
git add llm-service/prepare_data.py
git commit -m "Add data preparation script for Loghub dataset"
git push

# Then commit the CSV
git add llm-service/data/labeled_logs.csv
git commit -m "Add labeled log dataset for DistilBERT training"
git push
```

---

### Step 5 — Commit 10: train.py (Run on Colab, NOT Your Laptop)

**Why not your laptop:** DistilBERT fine-tuning on CPU takes hours. On Colab's
free T4 GPU it takes 20–40 minutes. Don't waste your time.

**How to run on Colab:**
1. Go to colab.research.google.com
2. Runtime → Change runtime type → T4 GPU
3. Upload `train.py` and `data/labeled_logs.csv`
4. Uncomment the Google Drive lines at the top (marked in the code)
5. Run it
6. Download the model zip from Drive to your Mac
7. Extract into `llm-service/models/distilbert-log/`

```python
"""
DistilBERT fine-tuning for log severity classification.
RUN ON GOOGLE COLAB WITH T4 GPU — not locally.

Steps:
1. colab.research.google.com
2. Runtime > Change runtime type > T4 GPU
3. Upload this file + data/labeled_logs.csv
4. Uncomment Drive lines (marked STEP A and STEP B)
5. Run
6. Download model.zip to Mac
7. Extract into llm-service/models/distilbert-log/
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification,
    Trainer,
    TrainingArguments,
)
import torch
from torch.utils.data import Dataset
import json
import os

# STEP A — Uncomment on Colab to save model to Drive (survives session end)
# from google.colab import drive
# drive.mount('/content/drive')

SAVE_DIR = "./models/distilbert-log"
# On Colab, switch to:
# SAVE_DIR = "/content/drive/MyDrive/llm-log-explainer/models/distilbert-log"

df = pd.read_csv("data/labeled_logs.csv")
print(f"Total samples: {len(df)}")
print(df['label'].value_counts())

num_labels = df['label_id'].nunique()
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['label_id'])

tokenizer = DistilBertTokenizerFast.from_pretrained("distilbert-base-uncased")

class LogDataset(Dataset):
    def __init__(self, texts, labels):
        self.encodings = tokenizer(list(texts), truncation=True, padding=True, max_length=128)
        self.labels = list(labels)
    def __len__(self): return len(self.labels)
    def __getitem__(self, idx):
        item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

train_dataset = LogDataset(train_df['text'], train_df['label_id'])
test_dataset  = LogDataset(test_df['text'],  test_df['label_id'])

model = DistilBertForSequenceClassification.from_pretrained(
    "distilbert-base-uncased", num_labels=num_labels
)

training_args = TrainingArguments(
    output_dir=SAVE_DIR,
    num_train_epochs=4,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    logging_steps=10,
    report_to="none",
)

trainer = Trainer(model=model, args=training_args,
                  train_dataset=train_dataset, eval_dataset=test_dataset)
trainer.train()

os.makedirs(SAVE_DIR, exist_ok=True)
model.save_pretrained(SAVE_DIR)
tokenizer.save_pretrained(SAVE_DIR)

label_names = sorted(df['label'].unique())
label_map = {i: label for i, label in enumerate(label_names)}
with open(os.path.join(SAVE_DIR, "label_map.json"), "w") as f:
    json.dump(label_map, f, indent=2)

print(f"Model saved to {SAVE_DIR}")
print(f"Label map: {label_map}")

# STEP B — Uncomment on Colab to download model after training:
# import shutil
# from google.colab import files
# shutil.make_archive("distilbert-log", "zip", SAVE_DIR)
# files.download("distilbert-log.zip")
```

```bash
git add llm-service/train.py
git commit -m "Add DistilBERT fine-tuning training script for Colab"
git push
```

**What success looks like after training:** You have a folder
`models/distilbert-log/` containing at minimum: `config.json`,
`pytorch_model.bin`, `tokenizer.json`, `tokenizer_config.json`,
`special_tokens_map.json`, `vocab.txt`, `label_map.json`.
The `label_map.json` should look like: `{"0": "HIGH", "1": "LOW", "2": "MEDIUM"}`
(alphabetical order — that's what LabelEncoder does).

---

### Step 6 — Commit 11: evaluate.py

Run this locally after downloading the model from Colab. It generates the
eval report which you show the teacher.

```python
"""
Run locally after downloading model from Colab.
Generates eval_report.txt with accuracy, F1, and confusion matrix.
"""
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification
from sklearn.metrics import classification_report, confusion_matrix
import pandas as pd
import torch
import json
import os

MODEL_DIR = "./models/distilbert-log"

tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_DIR)
model = DistilBertForSequenceClassification.from_pretrained(MODEL_DIR)
model.eval()

with open(os.path.join(MODEL_DIR, "label_map.json")) as f:
    label_map = {str(k): v for k, v in json.load(f).items()}

# label_id is already in the CSV from prepare_data.py
df = pd.read_csv("data/labeled_logs.csv")
test_df = df.sample(min(200, len(df)), random_state=99).reset_index(drop=True)

inputs = tokenizer(list(test_df['text']), truncation=True, padding=True,
                   max_length=128, return_tensors="pt")

with torch.no_grad():
    outputs = model(**inputs)
    preds = torch.argmax(outputs.logits, dim=1).numpy()

true_labels = [label_map[str(lid)] for lid in test_df['label_id']]
pred_labels = [label_map[str(p)] for p in preds]

ordered = sorted(label_map.values())
report = classification_report(true_labels, pred_labels, labels=ordered)
matrix = confusion_matrix(true_labels, pred_labels, labels=ordered)

print(report)
print(f"Confusion Matrix {ordered}:\n{matrix}")

os.makedirs("models", exist_ok=True)
with open("models/eval_report.txt", "w") as f:
    f.write("LLM Log Explainer — DistilBERT Evaluation\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"Test samples: {len(test_df)}\n")
    f.write(f"Labels: {ordered}\n\n")
    f.write("Classification Report\n" + "-" * 50 + "\n")
    f.write(report)
    f.write(f"\nConfusion Matrix {ordered}\n" + "-" * 50 + "\n")
    f.write(str(matrix))

print("Saved to models/eval_report.txt")
```

```bash
cd llm-service
python evaluate.py   # run it, check it prints reasonable accuracy

git add llm-service/evaluate.py
git commit -m "Add model evaluation script with classification report and confusion matrix"
git push
```

---

### Step 7 — Commit 12: Push Trained Model

This is where Git LFS matters. The `.bin` file is ~250MB. Do this:

```bash
# Make sure LFS is installed on your machine
git lfs install

# Add the model files
cd ~/llm-log-explainer
git add llm-service/models/distilbert-log/
git add llm-service/models/eval_report.txt
git commit -m "Add trained DistilBERT model weights and evaluation report"
git push   # LFS handles the .bin file automatically
```

**What success looks like:** On GitHub, clicking on `pytorch_model.bin` should
show a Git LFS pointer page, not a download of raw binary. It'll say something
like "Stored with Git LFS".

---

### Step 8 — Commit 13: prompts.py

This is the knowledge base — explanation templates per severity level, and
root cause / recommended actions per scenario type.

```python
EXPLANATION_TEMPLATES = {
    'HIGH': {
        'prefix': 'CRITICAL ISSUE DETECTED.',
        'action': 'Immediate investigation required. Check relevant service logs, alert on-call team.',
    },
    'MEDIUM': {
        'prefix': 'Potential issue identified.',
        'action': 'Monitor closely. Investigate if this pattern recurs within the next hour.',
    },
    'LOW': {
        'prefix': 'Normal operation recorded.',
        'action': 'No immediate action required. Archive for audit trail.',
    },
}

SCENARIO_PATTERNS = {
    'database_failure': {
        'root_cause': 'Database server became unreachable after multiple retry attempts. Likely caused by network partition, database process crash, or resource exhaustion.',
        'actions': [
            'Check database server health: ping, process status, disk space',
            'Review network configuration and firewall rules between app and database',
            'Verify connection pool settings and timeout values in app config',
        ],
    },
    'auth_breach': {
        'root_cause': 'Rapid successive failed login attempts from a single IP indicate a brute force attack targeting admin account.',
        'actions': [
            'Immediately review firewall rules and block the attacking IP',
            'Implement rate limiting on authentication endpoints',
            'Enable multi-factor authentication for all admin accounts',
        ],
    },
    'memory_leak': {
        'root_cause': 'Memory leak in image_processor module causing gradual heap exhaustion leading to crash.',
        'actions': [
            'Profile image_processor module for object retention and unclosed streams',
            'Implement memory usage alerts at 70% threshold',
            'Schedule regular application restarts as a temporary measure',
        ],
    },
    'api_overload': {
        'root_cause': 'Traffic spike exhausted API rate limits faster than auto-scaling could respond.',
        'actions': [
            'Lower auto-scaling trigger threshold from 90% to 70% utilization',
            'Implement request queuing instead of hard rejection at rate limit',
            'Add CDN caching layer for read-heavy endpoints',
        ],
    },
    'disk_failure': {
        'root_cause': 'Physical disk degradation with increasing SMART reallocated sector count. Failover triggered.',
        'actions': [
            'Schedule immediate physical disk replacement',
            'Verify backup volume integrity and available space',
            'Set up automated SMART monitoring alerts',
        ],
    },
}
```

```bash
git add llm-service/prompts.py
git commit -m "Add explanation templates and scenario pattern knowledge base"
git push
```

---

### Step 9 — Commit 14: api.py (The Main FastAPI App)

This is the core of your service. It loads the model once at startup, exposes
3 endpoints, and uses the model to classify + explain logs.

```python
"""
LLM Service — FastAPI app using fine-tuned DistilBERT for log classification.
"""
import os, json, requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification
import torch
from prompts import EXPLANATION_TEMPLATES, SCENARIO_PATTERNS

app = FastAPI(title="LLM Log Explainer Service", version="2.0.0")

LOG_GENERATOR_URL = os.environ.get("LOG_GENERATOR_URL", "http://log-generator:5000")
MODEL_DIR = os.environ.get("MODEL_DIR", "./models/distilbert-log")

# Load once at startup
print(f"Loading model from {MODEL_DIR}...")
tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_DIR)
model = DistilBertForSequenceClassification.from_pretrained(MODEL_DIR)
model.eval()
with open(os.path.join(MODEL_DIR, "label_map.json")) as f:
    label_map = {str(k): v for k, v in json.load(f).items()}
print(f"Model loaded. Labels: {label_map}")


# --- Schemas ---

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


# --- Core logic ---

def classify(message: str) -> str:
    inputs = tokenizer(message, truncation=True, padding=True,
                       max_length=128, return_tensors="pt")
    with torch.no_grad():
        pred_id = torch.argmax(model(**inputs).logits, dim=1).item()
    return label_map[str(pred_id)]

def explain(log: LogEntry) -> LogExplanation:
    severity = classify(log.message)
    t = EXPLANATION_TEMPLATES.get(severity, EXPLANATION_TEMPLATES['LOW'])
    return LogExplanation(
        log_id=log.id,
        explanation=(
            f"{t['prefix']} The {log.context.module} module reported: "
            f'"{log.message}". Logged at {log.level} level on {log.timestamp}.'
        ),
        severity=severity.lower(),
        suggestion=t['action'],
    )


# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "healthy", "service": "llm-service",
            "model": "distilbert-log", "labels": list(label_map.values())}

@app.post("/explain", response_model=LogExplanation)
def explain_single(log: LogEntry):
    try: return explain(log)
    except Exception as e: raise HTTPException(500, str(e))

@app.post("/explain/batch")
def explain_batch(req: ExplainBatchRequest):
    try:
        explanations = [explain(log) for log in req.logs]
        if req.scenario and req.scenario in SCENARIO_PATTERNS:
            p = SCENARIO_PATTERNS[req.scenario]
            high = sum(1 for e in explanations if e.severity == "high")
            med  = sum(1 for e in explanations if e.severity == "medium")
            return {
                "scenario": req.scenario,
                "summary": (f"Analysed {len(explanations)} logs for '{req.scenario}'. "
                            f"{high} critical, {med} warnings. {p['root_cause']}"),
                "log_explanations": explanations,
                "root_cause": p['root_cause'],
                "recommended_actions": p['actions'],
            }
        return {"count": len(explanations), "explanations": explanations}
    except Exception as e: raise HTTPException(500, str(e))

@app.get("/fetch-and-explain")
def fetch_and_explain(scenario: Optional[str] = None):
    """Web interface calls this — fetches from log-generator then explains."""
    try:
        url = (f"{LOG_GENERATOR_URL}/scenario/{scenario}" if scenario
               else f"{LOG_GENERATOR_URL}/generate")
        data = requests.get(url, timeout=10).json()
    except Exception as e:
        raise HTTPException(503, f"Log generator unavailable: {e}")
    if "logs" in data:
        return explain_batch(ExplainBatchRequest(logs=[LogEntry(**l) for l in data["logs"]],
                                                  scenario=scenario))
    return explain_single(LogEntry(**data))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

```bash
git add llm-service/api.py
git commit -m "Implement FastAPI endpoints with trained DistilBERT model inference"
git push
```

---

## Testing Your Service Locally (Before Docker)

Once you have the model downloaded and api.py written, test it locally:

**Terminal 1 — Start my log generator:**
```bash
cd ~/llm-log-explainer/log-generator
pip install flask
python app.py   # runs on port 5001 (macOS AirPlay conflict on 5000)
# OR if you disable AirPlay: python app.py runs on 5000
```

**Terminal 2 — Start your service:**
```bash
cd ~/llm-log-explainer/llm-service
pip install -r requirements.txt
LOG_GENERATOR_URL=http://localhost:5000 uvicorn api:app --port 8000 --reload
```

**Terminal 3 — Test:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/fetch-and-explain
curl "http://localhost:8000/fetch-and-explain?scenario=database_failure"
```

**What success looks like:**
- `/health` returns `"status": "healthy"` with the label map
- `/fetch-and-explain` returns a JSON with `log_id`, `explanation`, `severity`, `suggestion`
- `/fetch-and-explain?scenario=database_failure` returns a full incident analysis
  with `root_cause` and `recommended_actions`

---

## The API Contract (Our Agreement — Don't Change It)

Everything runs through this JSON contract between our services:

**My service gives you (log format):**
```json
{
  "id": "uuid-string",
  "request_id": "req_abc123",
  "timestamp": "2026-03-11T14:30:00.000000",
  "level": "ERROR",
  "message": "Database connection timeout after 30 seconds",
  "context": {"module": "db_handler", "line": 142, "process_id": 9210}
}
```

**Your service returns (explanation format):**
```json
{
  "log_id": "uuid-string",
  "explanation": "CRITICAL ISSUE DETECTED. The db_handler module reported: ...",
  "severity": "high",
  "suggestion": "Immediate investigation required..."
}
```

**For scenario batch (your service returns):**
```json
{
  "scenario": "database_failure",
  "summary": "Analysed 10 logs...",
  "log_explanations": [...],
  "root_cause": "Database server became unreachable...",
  "recommended_actions": ["Check database server health...", "..."]
}
```

---

## Common Mistakes — Don't Do These

- **Don't train on your laptop.** Seriously, use Colab.
- **Don't push `pytorch_model.bin` without git lfs install running first.**
  GitHub will reject it and you'll have to redo the commit.
- **Don't commit `raw_logs/`** — the Loghub files are big and irrelevant to code history.
- **Don't bundle all your work into one commit.** One file/task per commit.
  Portfolio marks literally depend on this.
- **Don't change any endpoint URLs in my log-generator** — the web interface
  and your api.py already reference them.
- **When running inside Docker**, talk to my service as `http://log-generator:5000`
  not `http://localhost:5000`. The environment variable `LOG_GENERATOR_URL` in
  docker-compose handles this — you don't need to hardcode it.

---

## Sync Points — After you are done with the work

**After you push Commit 7 (Dockerfile + requirements):**
Tell me so I can verify docker-compose.yml references the right build path.

**After you have api.py locally working:**
Let's do a joint test — I'll run my container, you run yours, we hit
`/fetch-and-explain` and make sure the JSON flows end to end before we
containerize everything.

**After `docker-compose up --build` works for the first time:**
This is the big one. Both containers talking to each other. We test every
scenario button before writing the web interface.

---

## What We're Showing the Teacher

1. `docker-compose up --build` — all 3 containers start, no errors
2. Web interface at `localhost:3000` — logs and explanations side by side
3. `models/eval_report.txt` — your accuracy, F1 score, confusion matrix
4. `train.py` — actual training code, not an API call
5. Live demo: hit "Database Failure" → 10 logs → root cause analysis appears

The eval report is the proof. Make sure accuracy is reasonable — if it's below 60% on all
classes, something went wrong with the data preparation or training.

---
