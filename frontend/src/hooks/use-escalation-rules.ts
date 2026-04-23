"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

export type EscalationAction = "slack" | "email" | "call";

export interface EscalationCondition {
  type: string;
  threshold?: number;
  window_minutes?: number;
  [key: string]: unknown;
}

export interface EscalationRule {
  id: string;
  tenant_id: string;
  name: string;
  condition: Record<string, unknown>;
  action: EscalationAction;
  is_active: boolean;
  created_at: string;
}

export interface EscalationRuleCreate {
  name: string;
  condition: EscalationCondition;
  action: EscalationAction;
}

export interface EscalationRuleUpdate {
  name?: string;
  condition?: EscalationCondition;
  action?: EscalationAction;
  is_active?: boolean;
}

export function useEscalationRules() {
  const [rules, setRules] = useState<EscalationRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const generationRef = useRef(0);

  const refresh = useCallback(() => {
    const myGen = ++generationRef.current;
    setLoading(true);
    setError(null);
    api
      .get<EscalationRule[]>("/api/v1/escalations")
      .then((data) => {
        if (myGen !== generationRef.current) return;
        setRules(data);
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
      generationRef.current += 1;
    };
  }, [refresh]);

  return { rules, loading, error, refresh };
}

export async function createEscalationRule(
  data: EscalationRuleCreate,
): Promise<EscalationRule> {
  return api.post<EscalationRule>("/api/v1/escalations", data);
}

export async function updateEscalationRule(
  id: string,
  data: EscalationRuleUpdate,
): Promise<EscalationRule> {
  return api.patch<EscalationRule>(`/api/v1/escalations/${id}`, data);
}

export async function deleteEscalationRule(id: string): Promise<void> {
  await api.delete(`/api/v1/escalations/${id}`);
}
