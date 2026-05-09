"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login, fetchMe } from "@/lib/api";
import { saveTokens, useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const setAuth = useAuth((s) => s.setAuth);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await login(email, password);
      saveTokens(tokens.access_token, tokens.refresh_token);
      const orgs = await api.get("/organizations");
      if (orgs.data?.[0]?.id) localStorage.setItem("org_id", orgs.data[0].id);
      const me = await fetchMe();
      setAuth(me, tokens.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <form onSubmit={onSubmit} className="card w-full max-w-md space-y-4">
        <h1 className="font-heading text-2xl">Sign in to UNFYD.PIVOT</h1>
        <input
          className="input"
          placeholder="you@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          type="email"
          required
        />
        <input
          className="input"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          required
        />
        {error && <div className="text-sm text-red-500">{error}</div>}
        <button className="btn-primary w-full" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-sm opacity-70">
          New here? <Link href="/register" className="text-brand">Create a workspace</Link>
        </p>
      </form>
    </main>
  );
}
