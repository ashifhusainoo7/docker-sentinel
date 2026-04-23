"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CrashEvent } from "@/hooks/use-crashes";

export function useCrash(id: string | null) {
  const [crash, setCrash] = useState<CrashEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    if (!id) {
      setLoading(false);
      return () => {
        cancelled = true;
      };
    }
    api
      .get<CrashEvent>(`/api/v1/crashes/${id}`)
      .then((c) => {
        if (!cancelled) setCrash(c);
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
  }, [id]);

  return { crash, loading, error };
}
