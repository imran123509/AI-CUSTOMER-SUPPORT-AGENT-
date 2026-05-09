# UNFYD.PIVOT — System Design

## High-level architecture

```
                         ┌──────────────────────┐
                         │   Browser / Mobile   │
                         └─────────┬────────────┘
                                   │  HTTPS / WSS
                         ┌─────────▼────────────┐
                         │     NGINX / Ingress  │
                         └─────┬───────┬────────┘
                               │       │
         ┌─────────────────────┘       └─────────────────────┐
         │                                                     │
┌────────▼────────┐                                  ┌─────────▼─────────┐
│  Next.js (SSR)  │                                  │ FastAPI (async)    │
│  app.unfyd.io   │                                  │ api.unfyd.io       │
└─────────────────┘                                  └────┬───────┬───────┘
                                                          │       │
                                                          │       ├─► Gemini API
                                                          │       │   (LLM + Embeddings)
                                                          │       │
                                          ┌───────────────┴────┐  │
                                          │                    │  │
                                  ┌───────▼─────┐  ┌──────────▼──┴──┐
                                  │  PostgreSQL │  │    Redis        │
                                  │ (canonical) │  │ cache + memory  │
                                  └─────────────┘  │ + Streams (queue)│
                                                   └────────┬─────────┘
                                                            │
                                       ┌────────────────────┴──────────────────┐
                                       │                                       │
                              ┌────────▼────────┐                   ┌──────────▼──────────┐
                              │  Workers        │                   │  ChromaDB           │
                              │ (doc, events,   │                   │  per-org collections│
                              │  SLA monitor)   │                   └─────────────────────┘
                              └─────────────────┘
```

## Service responsibilities

The API service is stateless — it owns request/response cycles, JWT auth,
input validation, and orchestration. It writes the canonical state to
PostgreSQL, reads/writes hot conversation context to Redis, queries
ChromaDB for RAG, calls Gemini for LLM/embeddings, and emits events on
Redis Streams.

Workers are also stateless and horizontally scalable. The document
processor consumes `unfyd:docs`, parses uploaded files, chunks, embeds via
Gemini, and stores chunks in PostgreSQL plus vectors in ChromaDB. The
event aggregator consumes `unfyd:events` to update Redis-cached metrics
counters used by the analytics dashboard. The SLA monitor periodically
scans tickets for breaches and raises events.

The Next.js frontend is mostly client-rendered with SSR for first-load.
It calls the REST API for state and opens a WebSocket per active
conversation for real-time chat with token-by-token AI streaming.

## Multi-tenancy

Every business row is scoped by `organization_id`. ChromaDB collections
are namespaced as `org_<uuid>` so vector searches cannot cross tenants.
Memberships gate access; the API requires `X-Org-Id` to switch active
tenant when a user belongs to multiple workspaces.

## Memory architecture

Short-term memory is a Redis list per conversation, capped at 24 turns
with a TTL. When the window exceeds the cap, older turns are summarised
by Gemini and the summary replaces them, preserving long-context coherence
without unbounded prompt size. Long-term canonical state remains in
PostgreSQL `messages` plus `conversation.summary`. User preferences are
held in a Redis hash per user for cross-conversation personalisation.

## RAG pipeline

Uploads land on disk (or object storage in production) and are recorded
in PostgreSQL with status `pending`. The API publishes
`document.uploaded` to `unfyd:docs`. The document worker pulls the event,
parses the file (pypdf, python-docx, csv, plain text), chunks
(~1200 chars with 180 overlap), embeds via Gemini's embedding model, and
upserts into the org's Chroma collection. Each chunk is persisted in
PostgreSQL with its Chroma ID so we can reconcile or re-index.

At query time, the AI service embeds the user's message, asks Chroma for
top-k chunks within the org collection, and prepends them to the system
prompt with their document name as a citation hint.

## Real-time chat

Each WebSocket connection is bound to `(organization_id, conversation_id)`
in the in-memory `ConnectionManager`. Typing and read events fan out to
peers in the same room. AI replies stream token-by-token; the chat UI
applies them progressively. Human takeover flips the conversation status
and routes subsequent inbound messages as `agent` rather than into
Gemini.

## Resilience

External calls go through a circuit breaker plus tenacity retries. AI and
RAG endpoints are protected by per-user Redis sliding-window rate limits.
A health endpoint reports liveness; readiness checks Redis. Workers are
supervised — on crash they restart with exponential backoff. The HPA
scales backend pods 3→30 on CPU; consider custom metrics for AI queue
depth in production.

## Security

Passwords use bcrypt with a server-side pepper. JWTs split access (30 min)
from refresh (14 d) tokens; refresh rotates on use. Inputs validated by
Pydantic. SQL injection prevented by parameterised SQLAlchemy. File
uploads bounded by size and extension allowlist; filenames are stripped
of directory components and stored under uuid prefixes. CORS origins are
explicit. All sensitive operations write to `audit_logs`.

## Scalability story

PostgreSQL is the bottleneck for write-heavy workloads. Mitigations:
read replicas for analytics dashboards, partitioning `messages` by month
once volume warrants, moving audit logs to a cold store. Chroma can be
swapped for Pinecone or Weaviate behind the same `rag_service` interface.
Redis Streams suffices to single-region millions of events/day; for
multi-region or higher throughput, replace with Kafka — the publish/consume
abstraction in `app.core.events` keeps that swap small. The frontend is
fully cacheable behind a CDN.
