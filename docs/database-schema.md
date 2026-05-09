# Database Schema (PostgreSQL)

```
organizations(id, name, slug, plan, settings, created_at, updated_at)
users(id, email, full_name, password_hash, is_active, is_superuser, avatar_url, locale, created_at, updated_at)
memberships(id, organization_id, user_id, role, created_at, updated_at)
conversations(id, organization_id, user_id, assigned_agent_id, title, status, summary, sentiment, intent, tags, metadata_json, created_at, updated_at)
messages(id, conversation_id, sender_id, role, content, tokens, latency_ms, sentiment, read_by, metadata_json, created_at, updated_at)
tickets(id, organization_id, conversation_id, requester_id, assignee_id, subject, description, summary, category, status, priority,
        sla_first_response_at, sla_resolution_at, first_responded_at, resolved_at, csat_score, tags, metadata_json, created_at, updated_at)
ticket_notes(id, ticket_id, author_id, body, is_internal, created_at, updated_at)
knowledge_bases(id, organization_id, name, description, chroma_collection, created_at, updated_at)
documents(id, knowledge_base_id, organization_id, uploaded_by, filename, storage_path, mime_type, size_bytes, status, error,
          chunk_count, metadata_json, created_at, updated_at)
document_chunks(id, document_id, seq, content, tokens, chroma_id, created_at, updated_at)
audit_logs(id, organization_id, actor_id, action, target_type, target_id, metadata_json, created_at, updated_at)
```

## Key relationships

Each `organization` has many `memberships`, `conversations`, `tickets`,
`knowledge_bases`. Each `conversation` belongs to one organization, has
many `messages`, optionally has one `ticket`. Tickets escalate
conversations to a tracked workflow. Knowledge bases own documents which
own chunks; vectors live in ChromaDB and are referenced by `chroma_id`.

## Indexes

`users.email` (unique), `organizations.slug` (unique),
`memberships(organization_id, user_id)` (unique composite),
`conversations(organization_id, status)`, `messages.conversation_id`,
`tickets(organization_id, status)`, `tickets.assignee_id`,
`audit_logs.action`, `audit_logs.organization_id`.

## Enums

`membership_role`: owner, admin, agent, member.
`conversation_status`: open, ai_handling, human_handling, resolved, archived.
`message_role`: user, assistant, agent, system.
`ticket_status`: new, open, pending, resolved, closed.
`ticket_priority`: low, normal, high, urgent.
`document_status`: pending, processing, indexed, failed.

## Migration strategy

Alembic baseline at `0001_initial` recreates the schema from
`Base.metadata`. Subsequent migrations should be generated with
`alembic revision --autogenerate -m "describe"` after editing models.
