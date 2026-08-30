import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="font-heading text-5xl font-bold tracking-tight">AI Agent</h1>
        <p className="mt-3 text-xl opacity-80">
          AI-powered customer support, built for scale.
        </p>
        <p className="mt-6 leading-relaxed opacity-70">
          Multi-tenant, RAG-grounded conversations, real-time chat, ticketing,
          and analytics — one platform.
        </p>
        <div className="mt-10 flex justify-center gap-3">
          <Link href="/login" className="btn-primary">
            Sign in
          </Link>
          <Link href="/register" className="btn-ghost border" style={{ borderColor: "var(--border)" }}>
            Create workspace
          </Link>
        </div>
      </div>
    </main>
  );
}
