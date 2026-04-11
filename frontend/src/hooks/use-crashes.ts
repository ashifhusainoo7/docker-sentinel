"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface CrashEvent {
  id: string;
  container_name: string;
  image: string;
  exit_code: number | null;
  severity: string | null;
  category: string | null;
  root_cause: string | null;
  created_at: string;
}

export function useCrashes(limit = 50) {
  const [crashes, setCrashes] = useState<CrashEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<CrashEvent[]>(`/api/v1/crashes?limit=${limit}`)
      .then(setCrashes)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [limit]);

  return { crashes, loading, error };
}
