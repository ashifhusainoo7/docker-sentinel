"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { isAuthenticated, clearTokens } from "@/lib/auth";

interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  role: string;
}

interface AuthState {
  user: User | null;
  tenantName: string | null;
  loading: boolean;
  logout: () => void;
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<User | null>(null);
  const [tenantName, setTenantName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      setLoading(false);
      return;
    }

    api
      .get<{ user: User; tenant_name: string }>("/api/v1/auth/me")
      .then((data) => {
        setUser(data.user);
        setTenantName(data.tenant_name);
      })
      .catch(() => {
        clearTokens();
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = () => {
    clearTokens();
    setUser(null);
    window.location.href = "/login";
  };

  return { user, tenantName, loading, logout };
}
