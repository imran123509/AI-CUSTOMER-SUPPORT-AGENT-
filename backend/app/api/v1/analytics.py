"""Analytics dashboard REST endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentMembership, DBSession
from app.schemas.analytics import DashboardSummary, Timeseries, TimeseriesPoint
from app.services import analytics_service

router = APIRouter()


@router.get("/dashboard", response_model=DashboardSummary)
async def dashboard(membership: CurrentMembership, session: DBSession):
    data = await analytics_service.dashboard_summary(session, membership.organization_id)
    return DashboardSummary(**data)


@router.get("/messages/daily", response_model=Timeseries)
async def message_volume(
    membership: CurrentMembership, session: DBSession, days: int = 14
):
    rows = await analytics_service.daily_message_volume(
        session, membership.organization_id, days=days
    )
    return Timeseries(metric="messages_daily", points=[TimeseriesPoint(**r) for r in rows])


@router.get("/agents")
async def agent_productivity(membership: CurrentMembership, session: DBSession):
    return await analytics_service.agent_productivity(session, membership.organization_id)
