"""Drop the UNIQUE constraint on knowledge_bases.chroma_collection.

Revision ID: 0002_kb_collection_not_unique
Revises: 0001_initial
Create Date: 2026-08-30

`chroma_collection` is derived solely from the organization id, while
`rag_service` namespaces Chroma collections per organization.  The UNIQUE
constraint therefore allowed exactly one knowledge base per organization --
creating a second one raised UniqueViolationError and returned a 500.  Replace
it with a plain index, which is what the lookups actually need.
"""
from __future__ import annotations

from alembic import op

revision = "0002_kb_collection_not_unique"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "knowledge_bases_chroma_collection_key", "knowledge_bases", type_="unique"
    )
    op.create_index(
        "ix_knowledge_bases_chroma_collection",
        "knowledge_bases",
        ["chroma_collection"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_bases_chroma_collection", table_name="knowledge_bases")
    op.create_unique_constraint(
        "knowledge_bases_chroma_collection_key", "knowledge_bases", ["chroma_collection"]
    )
