"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { register } from "@/lib/api";
import { saveTokens, useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    organization_name: "",
  });
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const setAuth = useAuth((s) => s.setAuth);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const tokens = await register(form);
      saveTokens(tokens.access_token, tokens.refresh_token);
      setAuth({ id: "", email: form.email, full_name: form.full_name }, tokens.access_token);
      router.push("/dashboard");
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  function update<K extends keyof typeof form>(k: K, v: string) {
    setForm({ ...form, [k]: v });
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <form onSubmit={onSubmit} className="card w-full max-w-md space-y-4">
        <h1 className="font-heading text-2xl">Create your workspace</h1>
        <input className="input" placeholder="Workspace name" value={form.organization_name} onChange={(e) => update("organization_name", e.target.value)} required />
        <input className="input" placeholder="Your full name" value={form.full_name} onChange={(e) => update("full_name", e.target.value)} required />
        <input className="input" placeholder="you@company.com" value={form.email} onChange={(e) => update("email", e.target.value)} type="email" required />
        <input className="input" placeholder="Password (min 8)" value={form.password} onChange={(e) => update("password", e.target.value)} type="password" minLength={8} required />
        {err && <div className="text-sm text-red-500">{err}</div>}
        <button className="btn-primary w-full" disabled={loading}>
          {loading ? "Creating…" : "Create workspace"}
        </button>
      </form>
    </main>
  );
}
