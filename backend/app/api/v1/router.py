"""Aggregates all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import (
    ai,
    analytics,
    auth,
    conversations,
    knowledge_base,
    organizations,
    tickets,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
