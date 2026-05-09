# API Surface

Full machine-readable spec is generated at `/openapi.json` and rendered at
`/docs` (Swagger) and `/redoc`. This document is a high-level overview.

All routes are under `/api/v1` unless noted. All authenticated routes
expect `Authorization: Bearer <access_token>` and (for org-scoped
operations) `X-Org-Id: <uuid>`.

## Auth (`/auth`)

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/register` | `{email, password, full_name, organization_name}` | tokens |
| POST | `/login` | `{email, password}` | tokens |
| POST | `/refresh` | `{refresh_token}` | tokens |
| GET  | `/me` | — | user |

## Users (`/users`)

| Method | Path | |
|---|---|---|
| GET   | `/me` | current user profile |
| PATCH | `/me` | update full_name / locale / avatar_url |

## Organizations (`/organizations`)

| Method | Path | |
|---|---|---|
| GET   | `` | orgs the current user belongs to |
| GET   | `/current` | active org |
| PATCH | `/current` | (admin) update name/plan/settings |
| GET   | `/current/members` | list members |
| POST  | `/current/members` | (admin) invite by email |

## Conversations (`/conversations`)

| Method | Path | |
|---|---|---|
| GET   | `` | list (filter by status) |
| POST  | `` | create (with optional initial_message → triggers AI) |
| GET   | `/{id}` | detail with messages |
| GET   | `/{id}/messages` | paginated history |
| POST  | `/{id}/messages` | send a user message → AI replies (rate-limited) |
| POST  | `/{id}/stream` | server-sent stream variant |
| POST  | `/{id}/handoff` | (agent) move to human, materialise ticket |
| POST  | `/{id}/smart-replies` | (agent) AI-suggested replies |

## Tickets (`/tickets`)

| Method | Path | |
|---|---|---|
| GET   | `` | list (filter by status/assignee) |
| POST  | `` | create — auto-classify summary/category/priority |
| GET   | `/{id}` | detail |
| PATCH | `/{id}` | update |
| GET   | `/{id}/notes` | internal notes |
| POST  | `/{id}/notes` | add note |
| POST  | `/{id}/escalate` | (agent) human escalation |

## Knowledge Base (`/knowledge-base`)

| Method | Path | |
|---|---|---|
| GET   | `` | list KBs |
| POST  | `` | (admin) create KB |
| GET   | `/{kb_id}/documents` | list docs |
| POST  | `/{kb_id}/documents` | (admin, multipart) upload — async indexing |
| DELETE| `/{kb_id}/documents/{doc_id}` | (admin) remove + de-index |
| POST  | `/search` | semantic search across org's collection |

## Analytics (`/analytics`)

| Method | Path | |
|---|---|---|
| GET   | `/dashboard` | summary KPIs |
| GET   | `/messages/daily` | 14-day timeseries |
| GET   | `/agents` | agent productivity (resolved tickets / 30d) |

## AI utilities (`/ai`)

| Method | Path | |
|---|---|---|
| POST  | `/sentiment` | classify sentiment |
| POST  | `/intent` | classify intent |
| POST  | `/tags` | generate tags |
| POST  | `/summarize` | summarise transcript |
| POST  | `/translate` | translate text |
| POST  | `/faq` | generate FAQ entry |

## WebSockets

`GET /ws/conversations/{conversation_id}?token=<jwt>` — bidirectional chat.

Inbound events: `ping`, `typing` (`is_typing`), `read` (`message_id`),
`message` (`content`), `request_handoff`.

Outbound events: `connected`, `pong`, `typing`, `read`, `message`,
`ai_typing`, `ai_chunk`, `ai_complete`, `handoff`.
