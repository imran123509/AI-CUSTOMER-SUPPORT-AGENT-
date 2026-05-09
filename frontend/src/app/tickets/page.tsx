"use client";
import useSWR from "swr";
import { api } from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const PRIORITY_COLOR: Record<string, string> = {
  urgent: "bg-red-500/20 text-red-500",
  high: "bg-orange-500/20 text-orange-500",
  normal: "bg-blue-500/20 text-blue-500",
  low: "bg-gray-500/20 text-gray-500",
};

export default function TicketsPage() {
  const { data, mutate } = useSWR<any[]>("/tickets", fetcher);

  async function setStatus(id: string, status: string) {
    await api.patch(`/tickets/${id}`, { status });
    mutate();
  }

  return (
    <div>
      <h1 className="font-heading text-2xl">Tickets</h1>
      <p className="opacity-70">All open and recent tickets across your workspace.</p>
      <div className="card mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left opacity-70" style={{ borderColor: "var(--border)" }}>
              <th className="py-2">Subject</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Category</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data?.map((t) => (
              <tr key={t.id} className="border-b last:border-0" style={{ borderColor: "var(--border)" }}>
                <td className="py-2 font-medium">{t.subject}</td>
                <td><span className="rounded-full bg-gray-200/40 px-2 py-1 text-xs">{t.status}</span></td>
                <td><span className={`rounded-full px-2 py-1 text-xs ${PRIORITY_COLOR[t.priority] || ""}`}>{t.priority}</span></td>
                <td>{t.category || "—"}</td>
                <td className="space-x-2 text-right">
                  <button className="btn-ghost text-xs" onClick={() => setStatus(t.id, "resolved")}>Resolve</button>
                </td>
              </tr>
            ))}
            {!data?.length && <tr><td colSpan={5} className="py-6 text-center opacity-60">No tickets yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
