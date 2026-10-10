import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, loadToken, setToken } from "./api";

export type User = {
  user_id: string;
  name: string;
  email?: string;
};

type AuthValue = {
  status: "loading" | "user" | "null";
  user: User | null;
  signIn: (name: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

function randomId(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (ch) => {
    const rand = Math.floor(Math.random() * 16);
    const value = ch === "x" ? rand : (rand & 0x3) | 0x8;
    return value.toString(16);
  });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthValue["status"]>("loading");
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = await loadToken();
      if (!token) {
        if (!cancelled) setStatus("null");
        return;
      }
      try {
        const me = await api<{ user: User }>("/api/auth/me");
        if (cancelled) return;
        setUser(me.user);
        setStatus("user");
      } catch {
        await setToken(null);
        if (!cancelled) {
          setUser(null);
          setStatus("null");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      status,
      user,
      signIn: async (name: string) => {
        const result = await api<{ session_token: string; user: User }>("/api/auth/session", {
          method: "POST",
          body: JSON.stringify({ session_id: randomId(), name }),
        });
        await setToken(result.session_token);
        setUser(result.user);
        setStatus("user");
      },
      signOut: async () => {
        try {
          await api("/api/auth/logout", { method: "POST" });
        } catch {
          // The local token still has to go.
        }
        await setToken(null);
        setUser(null);
        setStatus("null");
      },
    }),
    [status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is missing");
  return value;
}
