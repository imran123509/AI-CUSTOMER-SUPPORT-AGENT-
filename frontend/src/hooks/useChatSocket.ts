"use client";
import { useEffect, useRef, useState } from "react";

type ChatEvent =
  | { type: "connected"; conversation_id: string }
  | { type: "message"; role: string; content: string; message_id?: string; created_at?: string }
  | { type: "ai_typing"; is_typing: boolean }
  | { type: "ai_chunk"; content: string }
  | { type: "ai_complete"; content: string }
  | { type: "typing"; user_id: string; is_typing: boolean }
  | { type: "read"; user_id: string; message_id: string }
  | { type: "handoff"; by: string }
  | { type: "pong" };

export function useChatSocket(conversationId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<ChatEvent[]>([]);
  const [aiTyping, setAiTyping] = useState(false);
  const [aiBuffer, setAiBuffer] = useState("");

  useEffect(() => {
    if (!conversationId) return;
    const baseWs = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
    const token = localStorage.getItem("access_token") || "";
    const url = `${baseWs.replace(/\/ws$/, "")}/ws/conversations/${conversationId}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data) as ChatEvent;
      setEvents((prev) => [...prev, data]);
      if (data.type === "ai_typing") setAiTyping(data.is_typing);
      if (data.type === "ai_chunk") setAiBuffer((b) => b + data.content);
      if (data.type === "ai_complete") setAiBuffer("");
    };

    return () => ws.close();
  }, [conversationId]);

  function send(payload: object) {
    wsRef.current?.send(JSON.stringify(payload));
  }

  function sendMessage(content: string) {
    send({ type: "message", content });
  }

  function sendTyping(isTyping: boolean) {
    send({ type: "typing", is_typing: isTyping });
  }

  function requestHandoff() {
    send({ type: "request_handoff" });
  }

  return { connected, events, aiTyping, aiBuffer, sendMessage, sendTyping, requestHandoff };
}
