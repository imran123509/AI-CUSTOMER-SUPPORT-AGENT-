"use client";
import useSWR from "swr";
import { api } from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function SettingsPage() {
  const { data: org } = useSWR("/organizations/current", fetcher);
  const { data: members } = useSWR("/organizations/current/members", fetcher);

  return (
    <div className="space-y-6">
      <h1 className="font-heading text-2xl">Settings</h1>
      <div className="card">
        <h2 className="font-heading">Organization</h2>
        {org && (
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between"><dt className="opacity-70">Name</dt><dd>{org.name}</dd></div>
            <div className="flex justify-between"><dt className="opacity-70">Slug</dt><dd>{org.slug}</dd></div>
            <div className="flex justify-between"><dt className="opacity-70">Plan</dt><dd>{org.plan}</dd></div>
          </dl>
        )}
      </div>
      <div className="card">
        <h2 className="font-heading">Members ({members?.length || 0})</h2>
        <ul className="mt-3 space-y-1 text-sm">
          {members?.map((m: any) => (
            <li key={m.id} className="flex justify-between border-b py-1 last:border-0" style={{ borderColor: "var(--border)" }}>
              <span>{m.user_id.slice(0, 12)}…</span>
              <span className="opacity-70">{m.role}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
