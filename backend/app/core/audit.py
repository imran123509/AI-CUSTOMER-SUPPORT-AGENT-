"""Audit logging helpers.

Each sensitive action (auth, ticket changes, KB uploads, agent assignment)
should call `audit_log()` to write a permanent trail.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def audit_log(
    session: AsyncSession,
    *,
    organization_id: UUID | None,
    actor_id: UUID | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    log = AuditLog(
        organization_id=organization_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=metadata or {},
    )
    session.add(log)
    await session.flush()
