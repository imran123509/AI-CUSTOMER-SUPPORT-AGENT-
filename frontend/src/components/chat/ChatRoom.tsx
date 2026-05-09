"use client";
import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { useChatSocket } from "@/hooks/useChatSocket";
import { Send } from "lucide-react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

interface Msg { id?: string; role: string; content: string; created_at?: string; }

export default function ChatRoom({ conversationId }: { conversationId: string }) {
  const { data: detail, mutate } = useSWR(`/conversations/${conversationId}`, fetcher);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<Msg[]>([]);
  const [streamingAi, setStreamingAi] = useState("");
  const scrollerRef = useRef<HTMLDivElement>(null);
  const { connected, events, aiTyping, sendMessage, sendTyping, requestHandoff } = useChatSocket(conversationId);

  // accumulate streaming chunks
  useEffect(() => {
    const last = events[events.length - 1];
    if (!last) return;
    if (last.type === "ai_chunk") setStreamingAi((s) => s + last.content);
    if (last.type === "ai_complete") {
      setStreamingAi("");
      mutate();
    }
    if (last.type === "message") mutate();
  }, [events, mutate]);

  useEffect(() => {
    scrollerRef.current?.scrollTo({ top: scrollerRef.current.scrollHeight, behavior: "smooth" });
  }, [detail, streamingAi, pending]);

  function onSubmit() {
    const text = draft.trim();
    if (!text) return;
    setPending((p) => [...p, { role: "user", content: text }]);
    sendMessage(text);
    setDraft("");
  }

  const messages = detail?.messages || [];
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: "var(--border)" }}>
        <div>
          <div className="font-heading">{detail?.title || "Conversation"}</div>
          <div className="text-xs opacity-60">{detail?.status} · {connected ? "live" : "offline"}</div>
        </div>
        <button className="btn-ghost text-sm" onClick={requestHandoff}>Talk to a human</button>
      </div>

      <div ref={scrollerRef} className="flex-1 space-y-3 overflow-auto py-3">
        {messages.map((m: Msg, i: number) => <Bubble key={m.id || i} role={m.role} content={m.content} />)}
        {pending.map((m, i) => <Bubble key={"p" + i} role={m.role} content={m.content} pending />)}
        {streamingAi && <Bubble role="assistant" content={streamingAi} streaming />}
        {aiTyping && !streamingAi && <div className="text-sm opacity-60">AI is typing…</div>}
      </div>

      <div className="flex gap-2 border-t pt-2" style={{ borderColor: "var(--border)" }}>
        <input
          className="input"
          placeholder="Type a message…"
          value={draft}
          onChange={(e) => { setDraft(e.target.value); sendTyping(true); }}
          onBlur={() => sendTyping(false)}
          onKeyDown={(e) => e.key === "Enter" && onSubmit()}
        />
        <button className="btn-primary flex items-center gap-1" onClick={onSubmit}>
          <Send size={14} /> Send
        </button>
      </div>
    </div>
  );
}

function Bubble({ role, content, pending, streaming }: { role: string; content: string; pending?: boolean; streaming?: boolean }) {
  const mine = role === "user";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${mine ? "bg-brand text-white" : "bg-gray-100 dark:bg-white/10"} ${pending ? "opacity-60" : ""}`}>
        {content}
        {streaming && <span className="ml-1 animate-pulse">▍</span>}
      </div>
    </div>
  );
}
