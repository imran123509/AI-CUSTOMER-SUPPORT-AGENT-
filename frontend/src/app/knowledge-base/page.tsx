"use client";
import { ChangeEvent, useEffect, useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function KnowledgeBasePage() {
  const { data: kbs, mutate: mutateKbs } = useSWR<any[]>("/knowledge-base", fetcher);
  const [active, setActive] = useState<string | null>(null);
  const { data: docs, mutate: mutateDocs } = useSWR<any[]>(
    active ? `/knowledge-base/${active}/documents` : null,
    fetcher
  );

  useEffect(() => { if (!active && kbs?.[0]) setActive(kbs[0].id); }, [kbs, active]);

  async function createKb() {
    const name = prompt("Knowledge base name?");
    if (!name) return;
    await api.post("/knowledge-base", { name });
    mutateKbs();
  }

  async function uploadFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !active) return;
    const fd = new FormData();
    fd.append("file", file);
    await api.post(`/knowledge-base/${active}/documents`, fd, { headers: { "Content-Type": "multipart/form-data" } });
    mutateDocs();
    e.target.value = "";
  }

  return (
    <div>
      <h1 className="font-heading text-2xl">Knowledge Base</h1>
      <p className="opacity-70">Upload PDFs, DOCX, TXT, CSV — AI Agent will index them for grounded AI replies.</p>

      <div className="mt-6 grid grid-cols-[260px_1fr] gap-4">
        <div className="card">
          <div className="flex items-center justify-between">
            <h2 className="font-heading">Bases</h2>
            <button className="btn-ghost text-sm" onClick={createKb}>+ New</button>
          </div>
          <div className="mt-2 space-y-1">
            {kbs?.map((k) => (
              <button
                key={k.id}
                onClick={() => setActive(k.id)}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm ${active === k.id ? "bg-brand text-white" : "hover:bg-gray-100 dark:hover:bg-white/5"}`}
              >
                {k.name}
              </button>
            ))}
            {!kbs?.length && <div className="text-sm opacity-60">No knowledge bases yet.</div>}
          </div>
        </div>

        <div className="card">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-heading">Documents</h2>
            {active && (
              <label className="btn-primary cursor-pointer text-sm">
                Upload
                <input type="file" className="hidden" onChange={uploadFile} accept=".pdf,.docx,.txt,.csv,.md" />
              </label>
            )}
          </div>
          <div className="space-y-2">
            {docs?.map((d) => (
              <div key={d.id} className="flex items-center justify-between rounded-lg border p-3" style={{ borderColor: "var(--border)" }}>
                <div>
                  <div className="font-medium">{d.filename}</div>
                  <div className="text-xs opacity-60">{d.mime_type} · {(d.size_bytes / 1024).toFixed(1)} KB · {d.chunk_count} chunks</div>
                </div>
                <span className="rounded-full bg-gray-200/40 px-2 py-1 text-xs">{d.status}</span>
              </div>
            ))}
            {active && !docs?.length && <div className="text-sm opacity-60">No documents yet — upload one to get started.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
