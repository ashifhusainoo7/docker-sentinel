"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

export type NotificationChannel = "slack" | "email" | "voice";

export interface NotificationConfig {
  id: string;
  tenant_id: string;
  channel: NotificationChannel;
  is_enabled: boolean;
  use_platform_default: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface NotificationConfigUpdate {
  is_enabled?: boolean;
  use_platform_default?: boolean;
  config?: Record<string, unknown>;
}

export function useNotificationConfigs() {
  const [configs, setConfigs] = useState<NotificationConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const generationRef = useRef(0);

  const refresh = useCallback(() => {
    const myGen = ++generationRef.current;
    setLoading(true);
    setError(null);
    api
      .get<NotificationConfig[]>("/api/v1/notifications/config")
      .then((data) => {
        if (myGen !== generationRef.current) return;
        setConfigs(data);
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

  return { configs, loading, error, refresh };
}

export async function updateNotificationConfig(
  channel: NotificationChannel,
  data: NotificationConfigUpdate,
): Promise<NotificationConfig> {
  return api.put<NotificationConfig>(`/api/v1/notifications/config/${channel}`, data);
}

export async function testNotificationChannel(
  channel: NotificationChannel,
  message = "Test from DockerSentinel",
): Promise<unknown> {
  return api.post<unknown>(`/api/v1/notifications/test/${channel}`, { message });
}
