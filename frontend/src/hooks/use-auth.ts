"use client";

import { useEffect, useState } from "react";
import { getMe, logout as backendLogout, type UserPayload } from "@/lib/auth";

interface AuthState {
  user: UserPayload | null;
  tenantName: string | null;
  loading: boolean;
  logout: () => Promise<void>;
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<UserPayload | null>(null);
  const [tenantName, setTenantName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then((data) => {
        if (data) {
          setUser(data.user);
          setTenantName(data.tenant_name);
        }
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

  return { user, tenantName, loading, logout };
}
