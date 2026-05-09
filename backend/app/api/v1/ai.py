"""Standalone AI utilities: translation, sentiment, FAQ, summary."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import CurrentMembership
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.services import ai_service

router = APIRouter()
settings = get_settings()
ai_rate = RateLimiter(per_minute=60, key_prefix="rl:ai")


class TextIn(BaseModel):
    text: str


class TranslateIn(BaseModel):
    text: str
    target_language: str


class SummaryIn(BaseModel):
    text: str


@router.post("/sentiment", dependencies=[Depends(ai_rate)])
async def sentiment(payload: TextIn, _: CurrentMembership):
    if not settings.feature_sentiment:
        return {"label": "neutral", "disabled": True}
    return {"label": await ai_service.classify_sentiment(payload.text)}


@router.post("/intent", dependencies=[Depends(ai_rate)])
async def intent(payload: TextIn, _: CurrentMembership):
    return {"label": await ai_service.classify_intent(payload.text)}


@router.post("/tags", dependencies=[Depends(ai_rate)])
async def tags(payload: TextIn, _: CurrentMembership):
    return {"tags": await ai_service.generate_tags(payload.text)}


@router.post("/summarize", dependencies=[Depends(ai_rate)])
async def summarize(payload: SummaryIn, _: CurrentMembership):
    return {"summary": await ai_service.summarize_conversation(payload.text)}


@router.post("/translate", dependencies=[Depends(ai_rate)])
async def translate(payload: TranslateIn, _: CurrentMembership):
    if not settings.feature_translation:
        return {"translation": payload.text, "disabled": True}
    return {"translation": await ai_service.translate(payload.text, payload.target_language)}


@router.post("/faq", dependencies=[Depends(ai_rate)])
async def faq(payload: TextIn, _: CurrentMembership):
    if not settings.feature_faq_generation:
        return {"disabled": True}
    return await ai_service.generate_faq(payload.text)
