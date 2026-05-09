"use client";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import ChatRoom from "@/components/chat/ChatRoom";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function ChatPage() {
  const { data: convs, mutate } = useSWR<any[]>("/conversations", fetcher);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!selected && convs && convs[0]) setSelected(convs[0].id);
  }, [convs, selected]);

  async function newConversation() {
    const { data } = await api.post("/conversations", { title: "New conversation" });
    await mutate();
    setSelected(data.id);
  }

  return (
    <div className="grid h-[calc(100vh-3rem)] grid-cols-[280px_1fr] gap-4">
      <div className="card flex flex-col">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-lg">Conversations</h2>
          <button onClick={newConversation} className="btn-ghost text-sm">+ New</button>
        </div>
        <div className="mt-3 flex-1 space-y-1 overflow-auto">
          {convs?.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelected(c.id)}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm ${selected === c.id ? "bg-brand text-white" : "hover:bg-gray-100 dark:hover:bg-white/5"}`}
            >
              <div className="truncate font-medium">{c.title || "Untitled"}</div>
              <div className="text-xs opacity-70">{c.status}</div>
            </button>
          ))}
        </div>
      </div>
      <div className="card flex flex-col">
        {selected ? <ChatRoom conversationId={selected} /> : <div className="opacity-60">Select or create a conversation.</div>}
      </div>
    </div>
  );
}
