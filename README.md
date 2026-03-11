# LLM Log Explainer

Docker-based microservice system that generates realistic application logs
and uses a fine-tuned DistilBERT model to classify severity and explain
them in plain English.

## Architecture

Three containerized services orchestrated via Docker Compose:
- **log-generator** (Flask, port 5000): Generates realistic logs with 5 failure scenarios
- **llm-service** (FastAPI, port 8000): Fine-tuned DistilBERT classifier + explanation engine
- **web-interface** (HTML/JS, port 3000): Dashboard showing logs and explanations side by side

## Tech Stack
- Python 3.11, Flask, FastAPI, Uvicorn
- Hugging Face Transformers — DistilBERT fine-tuned on Loghub log data
- Docker + Docker Compose

## Team
- **Aaditya Upadhyay**: Docker, Infrastructure, Log Generator
- **Rasagya Vatsal**: LLM Service, Model Training, FastAPI endpoints

## Quick Start
\`\`\`bash
git lfs install && git lfs pull
docker-compose up --build
\`\`\`
- Log generator: http://localhost:5000
- LLM service:   http://localhost:8000
- Web interface: http://localhost:3000

## Log Generator Endpoints
| Endpoint | Description |
|----------|-------------|
| GET /health | Service health check |
| GET /generate | Random log entry |
| GET /generate?level=ERROR | Log by severity level |
| GET /generate/batch?count=10 | Multiple random logs |
| GET /scenario | List all failure scenarios |
| GET /scenario/database_failure | Database failure scenario |
| GET /scenario/auth_breach | Auth breach scenario |
| GET /scenario/memory_leak | Memory leak scenario |
| GET /scenario/api_overload | API overload scenario |
| GET /scenario/disk_failure | Disk failure scenario |

## LLM Service Endpoints
| Endpoint | Description |
|----------|-------------|
| GET /health | Service health check |
| POST /explain | Classify and explain a single log |
| POST /explain/batch | Explain multiple logs or full scenario |
| GET /fetch-and-explain | Auto-fetch from generator and explain |

## Model
The `models/` directory is tracked with Git LFS.
After cloning, run `git lfs pull` to download model weights.
See `models/eval_report.txt` for accuracy, F1 score, and confusion matrix.
