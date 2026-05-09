"""WebSocket routes — chat with typing indicators, read receipts, AI replies."""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

from app.core.database import session_scope
from app.core.logging import get_logger
from app.core.security import decode_token
from app.models.conversation import ConversationStatus
from app.models.message import MessageRole
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.repositories.organization import MembershipRepository
from app.services import ai_service, memory
from app.ws.manager import manager

logger = get_logger(__name__)
ws_router = APIRouter()


async def _authenticate(token: str | None) -> tuple[str, str] | None:
    """Return (user_id, org_id) for a valid access token."""
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    org_id = payload.get("org_id")
    if not sub:
        return None
    return str(sub), str(org_id) if org_id else ""


@ws_router.websocket("/ws/conversations/{conversation_id}")
async def chat_socket(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str = Query(default=""),
):
    auth = await _authenticate(token)
    if auth is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    user_id, _claim_org = auth

    # Validate membership + load conversation
    async with session_scope() as session:
        conv_repo = ConversationRepository(session)
        conv = await conv_repo.get(conversation_id)
        if not conv:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        member_repo = MembershipRepository(session)
        membership = await member_repo.for_org_user(conv.organization_id, UUID(user_id))
        if not membership:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        org_id = str(conv.organization_id)

    room = manager.room_key(org_id, str(conversation_id))
    await websocket.accept()
    await manager.join(room, websocket)

    await websocket.send_text(
        json.dumps({"type": "connected", "conversation_id": str(conversation_id)})
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            etype = event.get("type")

            if etype == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif etype == "typing":
                await manager.broadcast(
                    room,
                    {"type": "typing", "user_id": user_id, "is_typing": bool(event.get("is_typing", True))},
                    exclude=websocket,
                )

            elif etype == "read":
                msg_id = event.get("message_id")
                if msg_id:
                    await manager.broadcast(
                        room,
                        {"type": "read", "user_id": user_id, "message_id": msg_id},
                    )

            elif etype == "message":
                content = (event.get("content") or "").strip()
                if not content:
                    continue
                async with session_scope() as session:
                    conv_repo = ConversationRepository(session)
                    conv = await conv_repo.get(conversation_id)
                    if not conv:
                        break

                    if conv.status == ConversationStatus.HUMAN_HANDLING:
                        # Store as agent message; broadcast only — no AI
                        msg_repo = MessageRepository(session)
                        agent_msg = await msg_repo.add(
                            conversation_id=conv.id,
                            sender_id=UUID(user_id),
                            role=MessageRole.AGENT,
                            content=content,
                        )
                        await memory.append_turn(str(conv.id), "assistant", content)
                        await manager.broadcast(
                            room,
                            {
                                "type": "message",
                                "message_id": str(agent_msg.id),
                                "role": "agent",
                                "content": content,
                                "created_at": agent_msg.created_at.isoformat(),
                            },
                        )
                        continue

                    # AI-handled path: stream tokens
                    await manager.broadcast(
                        room,
                        {"type": "message", "role": "user", "content": content},
                        exclude=websocket,
                    )
                    accumulated: list[str] = []
                    await websocket.send_text(json.dumps({"type": "ai_typing", "is_typing": True}))
                    try:
                        async for chunk in ai_service.chat_stream(
                            session=session,
                            conversation=conv,
                            user_message_text=content,
                        ):
                            accumulated.append(chunk)
                            await manager.broadcast(
                                room, {"type": "ai_chunk", "content": chunk}
                            )
                    finally:
                        await websocket.send_text(
                            json.dumps({"type": "ai_typing", "is_typing": False})
                        )
                    full = "".join(accumulated)
                    await manager.broadcast(
                        room,
                        {"type": "ai_complete", "content": full},
                    )

            elif etype == "request_handoff":
                async with session_scope() as session:
                    conv_repo = ConversationRepository(session)
                    conv = await conv_repo.get(conversation_id)
                    if conv:
                        conv.status = ConversationStatus.HUMAN_HANDLING
                await manager.broadcast(
                    room,
                    {"type": "handoff", "by": user_id},
                )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("ws.error", error=str(exc))
    finally:
        await manager.leave(room, websocket)
