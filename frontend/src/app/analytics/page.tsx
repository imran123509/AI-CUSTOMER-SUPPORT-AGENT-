"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function AnalyticsPage() {
  const { data: timeseries } = useSWR("/analytics/messages/daily", fetcher);
  const { data: agents } = useSWR("/analytics/agents", fetcher);
  const points = timeseries?.points?.map((p: any) => ({ date: p.bucket?.slice(0, 10), value: p.value })) || [];
  const productivity = (agents || []).map((a: any) => ({ agent: a.agent_id?.slice(0, 8), resolved: a.resolved_count }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl">Analytics</h1>
        <p className="opacity-70">Operational KPIs and AI usage.</p>
      </div>

      <div className="card">
        <h2 className="font-heading">Daily messages (14d)</h2>
        <div className="mt-3 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points}>
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#5B5BD6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h2 className="font-heading">Agent productivity (30d resolved)</h2>
        <div className="mt-3 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={productivity}>
              <XAxis dataKey="agent" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="resolved" fill="#5B5BD6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
