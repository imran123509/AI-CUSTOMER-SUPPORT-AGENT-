import { create } from "zustand";

type User = { id: string; email: string; full_name: string };

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (user: User | null, token: string | null) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: null,
  setAuth: (user, token) => set({ user, token }),
  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("org_id");
    }
    set({ user: null, token: null });
  },
}));

export function saveTokens(access: string, refresh: string, orgId?: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
  if (orgId) localStorage.setItem("org_id", orgId);
}
