"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

// Recharts' default tooltip cursor is a solid #ccc rectangle sized to one
// category band.  On a dark card that reads as a grey slab, and with no data
// the band size degenerates to the full plot width -- which is why an empty
// chart looked like a blank white box.  Keep charts unmounted until there is
// something to plot, and tint the cursor to match the theme.
const CURSOR = { fill: "rgba(255,255,255,0.06)" };

function ChartFrame({
  title,
  isLoading,
  isEmpty,
  emptyHint,
  children,
}: {
  title: string;
  isLoading: boolean;
  isEmpty: boolean;
  emptyHint: string;
  children: React.ReactElement;
}) {
  return (
    <div className="card">
      <h2 className="font-heading">{title}</h2>
      <div className="mt-3 h-64">
        {isLoading || isEmpty ? (
          <div className="flex h-full flex-col items-center justify-center gap-1 text-center">
            <p className="text-sm opacity-70">{isLoading ? "Loading…" : "No data yet"}</p>
            {!isLoading && <p className="text-xs opacity-50">{emptyHint}</p>}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

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

      <ChartFrame
        title="Daily messages (14d)"
        isLoading={!timeseries}
        isEmpty={points.length === 0}
        emptyHint="Send a message in Chat and it will appear here."
      >
        <LineChart data={points}>
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip cursor={CURSOR} />
          <Line type="monotone" dataKey="value" stroke="#5B5BD6" strokeWidth={2} dot={false} />
        </LineChart>
      </ChartFrame>

      <ChartFrame
        title="Agent productivity (30d resolved)"
        isLoading={!agents}
        isEmpty={productivity.length === 0}
        emptyHint="Counts tickets resolved in the last 30 days that have an assignee."
      >
        <BarChart data={productivity}>
          <XAxis dataKey="agent" />
          <YAxis />
          <Tooltip cursor={CURSOR} />
          <Bar dataKey="resolved" fill="#5B5BD6" />
        </BarChart>
      </ChartFrame>
    </div>
  );
}
