"""Seed demo organization, users, and a starter knowledge base.

Run from the backend container:
    python -m scripts.seed
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import session_scope
from app.core.security import hash_password
from app.models.knowledge_base import KnowledgeBase
from app.models.organization import MembershipRole
from app.repositories.organization import (
    MembershipRepository,
    OrganizationRepository,
)
from app.repositories.user import UserRepository

DEMO_PASSWORD = "Demo1234!"

USERS: list[tuple[str, str, MembershipRole]] = [
    ("admin@demo.unfyd.io", "Demo Admin", MembershipRole.OWNER),
    ("agent@demo.unfyd.io", "Demo Agent", MembershipRole.AGENT),
    ("user@demo.unfyd.io", "Demo Customer", MembershipRole.MEMBER),
]


async def main() -> None:
    async with session_scope() as session:
        orgs = OrganizationRepository(session)
        users = UserRepository(session)
        members = MembershipRepository(session)

        org = await orgs.get_by_slug("demo")
        if not org:
            org = await orgs.create(name="Demo Workspace", slug="demo", plan="free")
            print(f"created org {org.name} ({org.id})")

        existing_kbs = (
            await session.execute(
                select(KnowledgeBase).where(KnowledgeBase.organization_id == org.id)
            )
        ).scalars().all()
        if not existing_kbs:
            session.add(
                KnowledgeBase(
                    organization_id=org.id,
                    name="General",
                    description="Default knowledge base",
                    chroma_collection=f"org_{str(org.id).replace('-', '')}",
                )
            )
            print("created default knowledge base")

        for email, full_name, role in USERS:
            user = await users.get_by_email(email)
            if not user:
                user = await users.create(
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(DEMO_PASSWORD),
                )
                print(f"created user {email}")
            membership = await members.for_org_user(org.id, user.id)
            if not membership:
                await members.add_member(org_id=org.id, user_id=user.id, role=role)
                print(f"added {email} as {role.value}")

    print("\nSeed complete.  Login with any of:")
    for email, *_ in USERS:
        print(f"  {email} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
