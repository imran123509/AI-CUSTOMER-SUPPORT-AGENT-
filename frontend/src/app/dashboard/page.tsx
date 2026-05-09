"use client";
import useSWR from "swr";
import { api } from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

function MetricCard({ title, value, suffix }: { title: string; value: string | number; suffix?: string }) {
  return (
    <div className="card">
      <div className="text-sm opacity-70">{title}</div>
      <div className="mt-1 text-3xl font-heading">{value}{suffix && <span className="ml-1 text-base opacity-60">{suffix}</span>}</div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: summary } = useSWR("/analytics/dashboard", fetcher);
  const m = summary || {};
  return (
    <div>
      <h1 className="font-heading text-2xl">Dashboard</h1>
      <p className="opacity-70">Live operational metrics across your organization.</p>
      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Active conversations" value={m.active_conversations ?? "—"} />
        <MetricCard title="Open tickets" value={m.open_tickets ?? "—"} />
        <MetricCard title="Resolved today" value={m.resolved_today ?? "—"} />
        <MetricCard title="CSAT (30d)" value={m.csat_30d != null ? Number(m.csat_30d).toFixed(2) : "—"} />
        <MetricCard title="Avg first response" value={m.avg_first_response_seconds != null ? Math.round(m.avg_first_response_seconds) : "—"} suffix="s" />
        <MetricCard title="Avg resolution" value={m.avg_resolution_seconds != null ? Math.round(m.avg_resolution_seconds / 60) : "—"} suffix="min" />
        <MetricCard title="AI response time" value={m.ai_response_time_ms_avg != null ? Math.round(m.ai_response_time_ms_avg) : "—"} suffix="ms" />
        <MetricCard title="Tokens (30d)" value={m.tokens_used_30d ?? "—"} />
      </div>
    </div>
  );
}
