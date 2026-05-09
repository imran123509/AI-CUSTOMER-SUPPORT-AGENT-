from __future__ import annotations

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    active_conversations: int
    open_tickets: int
    resolved_today: int
    avg_first_response_seconds: float | None
    avg_resolution_seconds: float | None
    csat_30d: float | None
    ai_response_time_ms_avg: float | None
    tokens_used_30d: int


class TimeseriesPoint(BaseModel):
    bucket: str
    value: float


class Timeseries(BaseModel):
    metric: str
    points: list[TimeseriesPoint]
