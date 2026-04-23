"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

export interface Member {
  id: string;
  email: string;
  name: string | null;
  role: string;
  created_at: string;
}

export interface MemberInvite {
  email: string;
  role: string;
}

export function useMembers() {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const generationRef = useRef(0);

  const refresh = useCallback(() => {
    const myGen = ++generationRef.current;
    setLoading(true);
    setError(null);
    api
      .get<Member[]>("/api/v1/tenants/current/members")
      .then((data) => {
        if (myGen !== generationRef.current) return;
        setMembers(data);
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

  return { members, loading, error, refresh };
}

export async function inviteMember(data: MemberInvite): Promise<unknown> {
  return api.post<unknown>("/api/v1/tenants/current/members/invite", data);
}
