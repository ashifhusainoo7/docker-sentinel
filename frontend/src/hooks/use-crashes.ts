"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface CrashEvent {
  id: string;
  tenant_id: string;
  docker_host_id: string;
  container_name: string;
  container_id: string;
  image: string;
  exit_code: number | null;
  logs: string | null;
  timestamp: string;
  root_cause: string | null;
  category: string | null;
  severity: string | null;
  confidence: number | null;
  suggestions: string[];
  restart_attempted: boolean;
  restart_success: boolean | null;
  cache_hit: boolean;
  slack_sent: boolean;
  email_sent: boolean;
  call_made: boolean;
  llm_provider: string | null;
  llm_latency_ms: number | null;
  resolved_at: string | null;
  created_at: string;
}

export interface CrashFilters {
  severity?: string;
  category?: string;
  limit?: number;
}

export function useCrashes(filters: CrashFilters = {}) {
  const { severity, category, limit = 50 } = filters;
  const [crashes, setCrashes] = useState<CrashEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  // Bump this to re-run the effect on manual refresh.
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ limit: String(limit) });
    if (severity) params.set("severity", severity);
    if (category) params.set("category", category);
    api
      .get<CrashEvent[]>(`/api/v1/crashes?${params.toString()}`)
      .then((d) => {
        if (!cancelled) setCrashes(d);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof Error ? e : new Error("fetch failed"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [severity, category, limit, refreshKey]);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  const prependCrash = useCallback(
    (c: CrashEvent) => {
      setCrashes((prev) => {
        if (prev.some((p) => p.id === c.id)) return prev;
        return [c, ...prev].slice(0, limit);
      });
    },
    [limit],
  );

  return { crashes, loading, error, refresh, prependCrash };
}
