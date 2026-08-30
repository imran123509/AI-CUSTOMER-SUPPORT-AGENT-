"""Shared field types for the API schemas."""
from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from pydantic import BeforeValidator


def _stringify_uuid(value: Any) -> Any:
    """Coerce a uuid.UUID into its string form, leaving anything else alone.

    The ORM maps primary/foreign keys onto ``PGUUID(as_uuid=True)``, so loading a
    row yields real ``uuid.UUID`` objects.  Pydantic v2 does not coerce those
    into ``str``, so a plain ``id: str`` annotation raises
    ``string_type`` and the endpoint returns 500.  Declaring the field as
    ``UUIDStr`` accepts both a UUID (from the ORM) and a string (from JSON
    request bodies) while keeping the Python-side type ``str``.
    """
    return str(value) if isinstance(value, UUID) else value


UUIDStr = Annotated[str, BeforeValidator(_stringify_uuid)]
