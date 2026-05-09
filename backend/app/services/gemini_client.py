"""Thin async wrapper around google-generativeai.

Adds: timeout, retries (tenacity), circuit breaker, embeddings,
streaming.  All Gemini I/O goes through this module.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, List

import google.generativeai as genai
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.circuit_breaker import get_breaker
from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    if not settings.gemini_api_key:
        logger.warning("gemini.no_api_key — running in stub mode")
    else:
        genai.configure(api_key=settings.gemini_api_key)
    _configured = True


_breaker = get_breaker("gemini", failure_threshold=5, recovery_seconds=30)


def _stub_response(prompt: str) -> str:
    return (
        "I'm a placeholder reply because the Gemini API key isn't configured. "
        "Set GEMINI_API_KEY in your environment to enable live responses. "
        f"You said: {prompt[:240]}"
    )


async def generate(
    *,
    system: str,
    history: List[dict],
    user_message: str,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> str:
    """Single-shot generation. `history` is a list of {role, content} dicts."""
    _configure()
    if not settings.gemini_api_key:
        return _stub_response(user_message)

    async def _call() -> str:
        model = genai.GenerativeModel(
            settings.gemini_model,
            system_instruction=system,
            generation_config={
                "temperature": temperature if temperature is not None else settings.gemini_temperature,
                "max_output_tokens": max_output_tokens or settings.gemini_max_output_tokens,
            },
        )
        chat_history = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
            for m in history
        ]
        chat = model.start_chat(history=chat_history)
        # SDK is synchronous → run in default executor
        loop = asyncio.get_running_loop()
        resp = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: chat.send_message(user_message)),
            timeout=settings.gemini_timeout_seconds,
        )
        return resp.text or ""

    async def _wrapped() -> str:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, max=4),
            retry=retry_if_exception_type((TimeoutError, ConnectionError)),
            reraise=True,
        ):
            with attempt:
                return await _call()
        return ""

    try:
        return await _breaker.call(_wrapped)
    except Exception as exc:
        logger.exception("gemini.generate_failed", error=str(exc))
        raise ExternalServiceError(f"Gemini error: {exc}") from exc


async def generate_stream(
    *,
    system: str,
    history: List[dict],
    user_message: str,
) -> AsyncIterator[str]:
    """Yield text chunks as Gemini streams them."""
    _configure()
    if not settings.gemini_api_key:
        for tok in _stub_response(user_message).split():
            await asyncio.sleep(0.01)
            yield tok + " "
        return

    model = genai.GenerativeModel(
        settings.gemini_model,
        system_instruction=system,
        generation_config={
            "temperature": settings.gemini_temperature,
            "max_output_tokens": settings.gemini_max_output_tokens,
        },
    )
    chat_history = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
        for m in history
    ]
    chat = model.start_chat(history=chat_history)

    loop = asyncio.get_running_loop()

    def _start_stream():
        return chat.send_message(user_message, stream=True)

    try:
        stream = await loop.run_in_executor(None, _start_stream)
        for chunk in stream:
            text = getattr(chunk, "text", "") or ""
            if text:
                yield text
    except Exception as exc:
        logger.exception("gemini.stream_failed", error=str(exc))
        raise ExternalServiceError(f"Gemini stream error: {exc}") from exc


async def embed(texts: List[str]) -> List[List[float]]:
    """Returns a list of embedding vectors."""
    _configure()
    if not settings.gemini_api_key:
        # 768-dim deterministic stub
        import hashlib

        def _hash_vec(t: str) -> List[float]:
            digest = hashlib.sha256(t.encode()).digest()
            return [(b - 127.5) / 127.5 for b in digest][:64]

        return [_hash_vec(t) for t in texts]

    loop = asyncio.get_running_loop()

    def _call():
        out: List[List[float]] = []
        for t in texts:
            resp = genai.embed_content(
                model=f"models/{settings.gemini_embedding_model}",
                content=t,
                task_type="retrieval_document",
            )
            out.append(list(resp["embedding"]))
        return out

    try:
        return await _breaker.call(lambda: loop.run_in_executor(None, _call))
    except Exception as exc:
        logger.exception("gemini.embed_failed", error=str(exc))
        raise ExternalServiceError(f"Gemini embedding error: {exc}") from exc
