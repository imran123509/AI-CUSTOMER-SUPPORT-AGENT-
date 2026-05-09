"""Initial schema (bootstrap autogen).

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01

This migration uses `Base.metadata.create_all` for the bootstrap schema; in
real deployments use `alembic revision --autogenerate` after this baseline.
"""
from __future__ import annotations

from alembic import op

from app.core.database import Base
from app import models  # noqa: F401  ensure registration

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
