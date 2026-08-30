# AI Agent — AI Customer Support Platform

A production-grade, multi-tenant AI customer support SaaS combining Intercom/Zendesk-style ticketing with modern AI agents, RAG knowledge bases, and real-time chat.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind |
| Backend | FastAPI (async) + Python 3.11 |
| Database | PostgreSQL 16 |
| Cache / Memory | Redis 7 |
| Vector DB | ChromaDB |
| Queue / Events | Redis Streams (Kafka-pluggable) |
| Real-time | WebSockets |
| AI | Google Gemini API |
| Reverse proxy | NGINX |
| Containers | Docker + Docker Compose + Kubernetes |
| CI | GitHub Actions |

## Repository Layout

```
AI-Customer-support-agent/
├── backend/                FastAPI service (auth, AI, RAG, tickets, WS, analytics)
├── frontend/               Next.js + TypeScript SaaS UI
├── nginx/                  Reverse proxy config
├── k8s/                    Kubernetes manifests
├── monitoring/             Prometheus / Grafana scrape configs
├── scripts/                Seed and load-test utilities
├── docs/                   System design + DB schema + API spec
├── .github/workflows/      CI pipeline
├── docker-compose.yml      One-command local stack
├── .env.example            All required environment variables
└── README.md               You are here
```

## Quick Start (Local)

```bash
# 1. Copy env template and fill in your Gemini key + secrets
cp .env.example .env
# edit .env — set GEMINI_API_KEY, JWT_SECRET, POSTGRES_PASSWORD

# 2. Bring the stack up
docker compose up --build

# 3. Apply migrations + seed demo data
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed

# 4. Open the app
# Frontend:    http://localhost:3000
# API:         http://localhost:8000
# Swagger:     http://localhost:8000/docs
# Redoc:       http://localhost:8000/redoc
# ChromaDB:    http://localhost:8001
```

## Demo Credentials (after seed)

```
admin@demo.unfyd.io / Demo1234!
agent@demo.unfyd.io / Demo1234!
user@demo.unfyd.io  / Demo1234!
```

## Architecture

See [`docs/system-design.md`](docs/system-design.md) for the full architecture, sequence diagrams, and scaling strategy. Database schema is in [`docs/database-schema.md`](docs/database-schema.md). API surface is in [`docs/api-spec.md`](docs/api-spec.md).

## Features

Authentication & multi-tenant orgs, JWT + refresh, RBAC. AI agent backed by Gemini with multi-turn context, streaming, conversation memory, fallback. RAG knowledge base with PDF/DOCX/TXT/CSV ingestion, chunking, embeddings, semantic retrieval, per-org isolation. Ticketing with AI summaries, categorization, priority, SLA, escalation, internal notes. Real-time WebSocket chat with typing, read receipts, AI-to-human handoff. Analytics dashboard with response time, resolution metrics, CSAT, token usage, agent productivity. Sentiment, intent, smart replies, FAQ generation, translation, summarization. Async architecture, Redis Streams events, background workers, rate limiting, circuit breakers, retries.

## Production Deployment

```bash
# Build images
docker build -t unfyd/pivot-backend:latest backend/
docker build -t unfyd/pivot-frontend:latest frontend/

# Apply Kubernetes manifests
kubectl apply -f k8s/
```

See [`k8s/README.md`](k8s/README.md) for namespace, secret, and ingress configuration.

## Testing

```bash
# Backend
cd backend && pytest -v

# Frontend
cd frontend && npm test

# Load test
locust -f scripts/load_test.py --host http://localhost:8000
```

## License

Proprietary — AI Agent.
