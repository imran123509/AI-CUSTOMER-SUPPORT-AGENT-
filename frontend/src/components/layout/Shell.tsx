"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/hooks/useTheme";
import {
  LayoutDashboard, MessageSquare, Ticket, Database,
  BarChart3, Settings, Sun, Moon, LogOut,
} from "lucide-react";
import clsx from "clsx";

const NAV = [
  { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { href: "/chat", label: "Chat", Icon: MessageSquare },
  { href: "/tickets", label: "Tickets", Icon: Ticket },
  { href: "/knowledge-base", label: "Knowledge Base", Icon: Database },
  { href: "/analytics", label: "Analytics", Icon: BarChart3 },
  { href: "/settings", label: "Settings", Icon: Settings },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, toggle } = useTheme();
  const logout = useAuth((s) => s.logout);

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 border-r p-4" style={{ borderColor: "var(--border)" }}>
        <div className="mb-8 px-2">
          <Link href="/dashboard" className="font-heading text-xl">AI Agent</Link>
        </div>
        <nav className="space-y-1">
          {NAV.map(({ href, label, Icon }) => {
            const active = pathname?.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
                  active ? "bg-brand text-white" : "hover:bg-gray-100 dark:hover:bg-white/5"
                )}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-8 space-y-1">
          <button onClick={toggle} className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-white/5">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <button
            onClick={() => { logout(); router.push("/login"); }}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-white/5"
          >
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
