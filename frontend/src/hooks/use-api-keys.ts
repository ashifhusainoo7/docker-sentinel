"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface ApiKeyCreated {
  id: string;
  name: string;
  key: string;
  key_prefix: string;
  scopes: string[];
  expires_at: string | null;
}

export interface ApiKeyCreate {
  name: string;
  scopes?: string[];
  expires_in_days?: number | null;
}

export function useApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const generationRef = useRef(0);

  const refresh = useCallback(() => {
    const myGen = ++generationRef.current;
    setLoading(true);
    setError(null);
    api
      .get<ApiKey[]>("/api/v1/api-keys")
      .then((data) => {
        if (myGen !== generationRef.current) return;
        setKeys(data);
      })
      .catch((e: unknown) => {
        if (myGen !== generationRef.current) return;
        setError(e instanceof Error ? e : new Error("fetch failed"));
      })
      .finally(() => {
        if (myGen !== generationRef.current) return;
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
    return () => {
      generationRef.current += 1; // discard any in-flight response
    };
  }, [refresh]);

  return { keys, loading, error, refresh };
}

export async function createApiKey(data: ApiKeyCreate): Promise<ApiKeyCreated> {
  return api.post<ApiKeyCreated>("/api/v1/api-keys", data);
}

export async function revokeApiKey(id: string): Promise<void> {
  await api.delete(`/api/v1/api-keys/${id}`);
}
