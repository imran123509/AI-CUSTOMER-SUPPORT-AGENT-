"""High-level AI orchestration: chat, classification, summaries, smart-reply.

This module composes Gemini + RAG + memory + persistence.  Routes call
into here; downstream concerns (DB writes, vector search) live in their own
services.
"""
from __future__ import annotations

import json
import re
import time
from typing import AsyncIterator, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish
from app.core.logging import get_logger
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.services import gemini_client, memory, prompts, rag_service

logger = get_logger(__name__)


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def _json_payload(raw: str) -> str:
    """Strip a markdown code fence so `json.loads` sees bare JSON.

    Gemini routinely answers a "reply with JSON" prompt as ```json ... ```.
    Without stripping the fence every json.loads below fails and the crude
    text fallback runs instead, which turned a tag list into
    ["```json", "[", "\"order-delay\""].
    """
    match = _FENCE_RE.match(raw)
    return match.group(1) if match else raw.strip()


def _history_for_gemini(window: list[dict]) -> List[dict]:
    """Filter window to user/assistant roles Gemini accepts."""
    out: List[dict] = []
    for m in window:
        if m["role"] in ("user", "assistant"):
            out.append({"role": m["role"], "content": m["content"]})
        elif m["role"] == "system":
            # convert system summary -> user note
            out.append({"role": "user", "content": f"[context] {m['content']}"})
    return out


async def chat_complete(
    *,
    session: AsyncSession,
    conversation: Conversation,
    user_message_text: str,
    use_rag: bool = True,
) -> Message:
    """Send a user message, generate AI reply, persist both, return assistant Message."""
    msg_repo = MessageRepository(session)
    conv_repo = ConversationRepository(session)

    user_msg = await msg_repo.add(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=user_message_text,
    )
    await memory.append_turn(str(conversation.id), "user", user_message_text)

    context_blocks: list[str] = []
    if use_rag:
        try:
            hits = await rag_service.semantic_search(
                organization_id=conversation.organization_id,
                query=user_message_text,
            )
            for h in hits:
                context_blocks.append(f"[{h['document_name']}] {h['content']}")
        except Exception as exc:
            logger.warning("rag.skip", error=str(exc))

    system_prompt = prompts.support_prompt_with_context(context_blocks)
    window = await memory.get_window(str(conversation.id))
    history = _history_for_gemini(window[:-1])  # exclude last user (sent separately)

    started = time.perf_counter()
    try:
        reply_text = await gemini_client.generate(
            system=system_prompt,
            history=history,
            user_message=user_message_text,
        )
    except Exception as exc:
        logger.exception("ai.generate_failed", error=str(exc))
        reply_text = (
            "I'm having trouble reaching the AI service right now. "
            "I've recorded your message and a human agent will follow up."
        )
        conversation.status = ConversationStatus.HUMAN_HANDLING
    latency_ms = int((time.perf_counter() - started) * 1000)

    assistant_msg = await msg_repo.add(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=reply_text,
        latency_ms=latency_ms,
        tokens=len(reply_text.split()),
    )
    await memory.append_turn(str(conversation.id), "assistant", reply_text)

    if conversation.status == ConversationStatus.OPEN:
        conversation.status = ConversationStatus.AI_HANDLING
    await session.flush()

    await publish(
        "unfyd:events",
        {
            "type": "ai.message",
            "organization_id": str(conversation.organization_id),
            "conversation_id": str(conversation.id),
            "message_id": str(assistant_msg.id),
            "latency_ms": latency_ms,
            "tokens": assistant_msg.tokens,
        },
    )
    return assistant_msg


async def chat_stream(
    *,
    session: AsyncSession,
    conversation: Conversation,
    user_message_text: str,
    use_rag: bool = True,
) -> AsyncIterator[str]:
    """Streaming variant — yields text chunks; final assistant message persisted at end."""
    msg_repo = MessageRepository(session)

    await msg_repo.add(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=user_message_text,
    )
    await memory.append_turn(str(conversation.id), "user", user_message_text)

    context_blocks: list[str] = []
    if use_rag:
        try:
            hits = await rag_service.semantic_search(
                organization_id=conversation.organization_id,
                query=user_message_text,
            )
            for h in hits:
                context_blocks.append(f"[{h['document_name']}] {h['content']}")
        except Exception as exc:
            logger.warning("rag.skip", error=str(exc))

    system_prompt = prompts.support_prompt_with_context(context_blocks)
    window = await memory.get_window(str(conversation.id))
    history = _history_for_gemini(window[:-1])

    accumulated: list[str] = []
    started = time.perf_counter()
    async for chunk in gemini_client.generate_stream(
        system=system_prompt, history=history, user_message=user_message_text
    ):
        accumulated.append(chunk)
        yield chunk
    latency_ms = int((time.perf_counter() - started) * 1000)

    full = "".join(accumulated).strip() or "(empty response)"
    await msg_repo.add(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=full,
        latency_ms=latency_ms,
        tokens=len(full.split()),
    )
    await memory.append_turn(str(conversation.id), "assistant", full)
    await session.commit()


# ------------------------- classification helpers -------------------------
async def _one_shot(system: str, user: str) -> str:
    return (await gemini_client.generate(system=system, history=[], user_message=user)).strip()


async def classify_sentiment(text: str) -> str:
    return (await _one_shot(prompts.SENTIMENT_SYSTEM, text)).lower().split()[0] if text else "neutral"


async def classify_intent(text: str) -> str:
    return (await _one_shot(prompts.INTENT_SYSTEM, text)).lower().split()[0] if text else "general_question"


async def classify_category(text: str) -> str:
    return (await _one_shot(prompts.CATEGORY_SYSTEM, text)).lower().split()[0] if text else "general"


async def classify_priority(text: str) -> str:
    return (await _one_shot(prompts.PRIORITY_SYSTEM, text)).lower().split()[0] if text else "normal"


async def generate_tags(text: str) -> list[str]:
    raw = await _one_shot(prompts.TAG_SYSTEM, text)
    try:
        parsed = json.loads(_json_payload(raw))
        if isinstance(parsed, list):
            return [str(t).lower() for t in parsed][:5]
    except Exception:
        pass
    return [t.strip().lower() for t in raw.replace(",", " ").split() if t.strip()][:5]


async def summarize_conversation(transcript: str) -> str:
    return await _one_shot(prompts.SUMMARY_SYSTEM, transcript)


async def smart_replies(transcript: str) -> list[str]:
    raw = await _one_shot(prompts.SMART_REPLY_SYSTEM, transcript)
    try:
        parsed = json.loads(_json_payload(raw))
        if isinstance(parsed, list):
            return [str(s) for s in parsed[:3]]
    except Exception:
        pass
    # fallback split by newline
    return [line.strip("- ").strip() for line in raw.splitlines() if line.strip()][:3]


async def generate_faq(transcript: str) -> dict:
    raw = await _one_shot(prompts.FAQ_SYSTEM, transcript)
    try:
        parsed = json.loads(_json_payload(raw))
        if isinstance(parsed, dict) and "question" in parsed:
            return parsed
    except Exception:
        pass
    return {"question": "Auto-FAQ", "answer": raw}


async def translate(text: str, target_language: str) -> str:
    user = f"Target language: {target_language}\n\nText:\n{text}"
    return await _one_shot(prompts.TRANSLATE_SYSTEM, user)


# --------------- background helpers used by workers -----------------------
async def enrich_conversation(session: AsyncSession, conversation: Conversation) -> None:
    """Recompute sentiment, intent, tags, summary for a conversation."""
    repo = MessageRepository(session)
    msgs = await repo.list_for_conversation(conversation.id, limit=200)
    if not msgs:
        return
    transcript = "\n".join(f"{m.role.value}: {m.content}" for m in msgs)
    conversation.sentiment = await classify_sentiment(transcript[-2000:])
    conversation.intent = await classify_intent(transcript[-2000:])
    conversation.tags = await generate_tags(transcript[-3000:])
    conversation.summary = await summarize_conversation(transcript[-6000:])
    await session.flush()
