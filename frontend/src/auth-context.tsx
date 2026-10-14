import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, loadToken, setToken } from "./api";

export type User = {
  user_id: string;
  name: string;
  email?: string;
  age_confirmed?: boolean;
};

type AuthValue = {
  status: "loading" | "user" | "null";
  user: User | null;
  signIn: (name: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  loginEmail: (email: string, password: string) => Promise<void>;
  linkEmail: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  confirmAge: () => Promise<void>;
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
    const timeout = setTimeout(() => {
      cancelled = true;
      setUser(null);
      setStatus("null");
    }, 15000);
    (async () => {
      try {
        const token = await loadToken();
        if (cancelled) return;
        if (!token) {
          setStatus("null");
          return;
        }
        const me = await api<{ user: User }>("/api/auth/me");
        if (cancelled) return;
        setUser(me.user);
        setStatus("user");
      } catch {
        try {
          await setToken(null);
        } catch {
          // Storage threw. The boot still has to leave the spinner.
        }
        if (!cancelled) {
          setUser(null);
          setStatus("null");
        }
      } finally {
        clearTimeout(timeout);
      }
    })();
    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      status,
      user,
      signIn: async (name: string) => {
        const result = await api<{ session_token: string; user: User }>("/api/auth/session", {
          method: "POST",
          body: JSON.stringify({ session_id: randomId(), name, age_confirmed: true }),
        });
        await setToken(result.session_token);
        setUser(result.user);
        setStatus("user");
      },
      register: async (name: string, email: string, password: string) => {
        const result = await api<{ session_token: string; user: User }>("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({ name, email, password, age_confirmed: true }),
        });
        await setToken(result.session_token);
        setUser(result.user);
        setStatus("user");
      },
      loginEmail: async (email: string, password: string) => {
        const result = await api<{ session_token: string; user: User }>("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        await setToken(result.session_token);
        setUser(result.user);
        setStatus("user");
      },
      linkEmail: async (email: string, password: string) => {
        const result = await api<{ user: User }>("/api/auth/link-email", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        setUser(result.user);
      },
      confirmAge: async () => {
        const result = await api<{ user: User }>("/api/account/age", {
          method: "POST",
          body: JSON.stringify({ confirmed: true }),
        });
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
