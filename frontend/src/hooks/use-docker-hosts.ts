"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface DockerHost {
  id: string;
  tenant_id: string;
  name: string;
  connection_mode: "tcp" | "agent";
  tcp_url: string | null;
  tls_enabled: boolean;
  agent_id: string | null;
  agent_last_seen: string | null;
  is_active: boolean;
  monitor_all_containers: boolean;
  container_filter: unknown[];
  status: string;
  status_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DockerHostCreate {
  name: string;
  connection_mode: "tcp" | "agent";
  tcp_url?: string | null;
  tls_enabled?: boolean;
  monitor_all_containers?: boolean;
  container_filter?: unknown[];
}

export function useDockerHosts() {
  const [hosts, setHosts] = useState<DockerHost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchHosts = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .get<DockerHost[]>("/api/v1/hosts")
      .then(setHosts)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e : new Error("fetch failed")),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchHosts();
  }, [fetchHosts]);

  return { hosts, loading, error, refresh: fetchHosts };
}

export async function createHost(data: DockerHostCreate): Promise<DockerHost> {
  return api.post<DockerHost>("/api/v1/hosts", data);
}

export async function deleteHost(id: string): Promise<void> {
  await api.delete(`/api/v1/hosts/${id}`);
}

export async function testHostConnection(id: string): Promise<unknown> {
  return api.post<unknown>(`/api/v1/hosts/${id}/test`);
}
