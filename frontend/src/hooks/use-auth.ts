"use client";

import { useEffect, useState } from "react";
import { getMe, logout as backendLogout, type UserPayload } from "@/lib/auth";

interface AuthState {
  user: UserPayload | null;
  tenantName: string | null;
  loading: boolean;
  error: Error | null;
  logout: () => Promise<void>;
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<UserPayload | null>(null);
  const [tenantName, setTenantName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    getMe()
      .then((data) => {
        if (data) {
          setUser(data.user);
          setTenantName(data.tenant_name);
        }
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e : new Error("Failed to load user"));
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = async () => {
    await backendLogout();
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  };

  return { user, tenantName, loading, error, logout };
}
