from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.organization import Membership, MembershipRole, Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug.lower())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class MembershipRepository(BaseRepository[Membership]):
    model = Membership

    async def for_user(self, user_id: UUID) -> list[Membership]:
        stmt = select(Membership).where(Membership.user_id == user_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def for_org_user(self, org_id: UUID, user_id: UUID) -> Membership | None:
        stmt = select(Membership).where(
            Membership.organization_id == org_id, Membership.user_id == user_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_org_members(self, org_id: UUID) -> list[Membership]:
        stmt = select(Membership).where(Membership.organization_id == org_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def add_member(
        self, *, org_id: UUID, user_id: UUID, role: MembershipRole
    ) -> Membership:
        return await self.create(organization_id=org_id, user_id=user_id, role=role)
