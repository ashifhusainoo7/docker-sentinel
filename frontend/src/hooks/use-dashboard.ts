"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface DashboardSummary {
  crashes_24h: number;
  restarts_24h: number;
  cache_hit_rate: number;
  active_hosts: number;
}

export interface DashboardMetrics {
  period: string;
  mttr_seconds: number | null;
  mttr_delta_pct: number | null;
  crashes_total: number;
  crashes_delta_pct: number | null;
  severity_breakdown: Record<string, number>;
  category_breakdown: Record<string, number>;
}

export interface TimelinePoint {
  t: string;
  crashes: number;
  restarts: number;
}

export interface DashboardTimeline {
  period: string;
  bucket: "hour" | "day";
  points: TimelinePoint[];
}

export type Period = "24h" | "7d" | "30d";

function useEndpoint<T>(path: string, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get<T>(path)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e : new Error("fetch failed"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error };
}

export function useDashboardSummary() {
  return useEndpoint<DashboardSummary>("/api/v1/dashboard/summary");
}

export function useDashboardMetrics(period: Period = "24h") {
  return useEndpoint<DashboardMetrics>(`/api/v1/dashboard/metrics?period=${period}`, [period]);
}

export function useDashboardTimeline(period: Period = "24h") {
  return useEndpoint<DashboardTimeline>(`/api/v1/dashboard/timeline?period=${period}`, [period]);
}
