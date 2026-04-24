"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace(/^http/, "ws");

export type WsStatus = "live" | "connecting" | "offline";

type Subscriber = (status: WsStatus, message: unknown) => void;

const state = {
  ws: null as WebSocket | null,
  status: "offline" as WsStatus,
  lastMessage: null as unknown,
  subscribers: new Set<Subscriber>(),
  reconnectAttempts: 0,
  reconnectTimer: null as ReturnType<typeof setTimeout> | null,
  heartbeatTimer: null as ReturnType<typeof setInterval> | null,
  tokenRefreshTimer: null as ReturnType<typeof setTimeout> | null,
  refCount: 0,
};

function setStatus(next: WsStatus) {
  state.status = next;
  notify();
}

function notify() {
  for (const fn of state.subscribers) fn(state.status, state.lastMessage);
}

function clearTimers() {
  if (state.reconnectTimer) clearTimeout(state.reconnectTimer);
  if (state.heartbeatTimer) clearInterval(state.heartbeatTimer);
  if (state.tokenRefreshTimer) clearTimeout(state.tokenRefreshTimer);
  state.reconnectTimer = null;
  state.heartbeatTimer = null;
  state.tokenRefreshTimer = null;
}

function scheduleReconnect() {
  if (state.refCount <= 0) return;
  const delay = Math.min(1000 * 2 ** state.reconnectAttempts, 30_000);
  state.reconnectAttempts += 1;
  state.reconnectTimer = setTimeout(() => {
    void connect();
  }, delay);
}

async function fetchToken(): Promise<string | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/ws-token`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { token: string; expires_in: number };
    return body.token;
  } catch {
    return null;
  }
}

async function connect() {
  if (state.refCount <= 0) return;
  if (typeof window === "undefined") return;
  if (state.ws && state.ws.readyState <= 1) return; // connecting or open

  setStatus("connecting");
  const token = await fetchToken();
  if (!token) {
    setStatus("offline");
    scheduleReconnect();
    return;
  }

  const url = `${WS_URL}/api/v1/ws/live?token=${encodeURIComponent(token)}`;
  const ws = new WebSocket(url);
  state.ws = ws;

  ws.onopen = () => {
    state.reconnectAttempts = 0;
    setStatus("live");
    // Heartbeat
    state.heartbeatTimer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ type: "ping" }));
        } catch {
          // ignore
        }
      }
    }, 25_000);
    // Token refresh 5s before expiry
    state.tokenRefreshTimer = setTimeout(
      () => {
        // Simply trigger a reconnect with a fresh token
        try {
          ws.close(1000, "token-refresh");
        } catch {
          // ignore
        }
      },
      (60 - 5) * 1000,
    );
  };

  ws.onmessage = (ev) => {
    try {
      state.lastMessage = JSON.parse(ev.data);
    } catch {
      state.lastMessage = ev.data;
    }
    notify();
  };

  ws.onerror = () => {
    // onclose will fire after this
  };

  ws.onclose = () => {
    if (state.heartbeatTimer) clearInterval(state.heartbeatTimer);
    state.heartbeatTimer = null;
    if (state.tokenRefreshTimer) clearTimeout(state.tokenRefreshTimer);
    state.tokenRefreshTimer = null;
    state.ws = null;
    setStatus("offline");
    scheduleReconnect();
  };
}

function disconnect() {
  clearTimers();
  if (state.ws) {
    try {
      state.ws.close(1000, "client-teardown");
    } catch {
      // ignore
    }
  }
  state.ws = null;
  state.reconnectAttempts = 0;
  setStatus("offline");
}

function subscribe(fn: Subscriber): () => void {
  state.subscribers.add(fn);
  return () => {
    state.subscribers.delete(fn);
  };
}

interface UseWebSocketOptions {
  /** Whether this consumer wants the connection open. Default true. */
  enabled?: boolean;
}

/**
 * Subscribe to the live crash-event stream. Internally uses a module-level
 * singleton connection so multiple consumers share one socket. Automatically
 * refreshes the short-lived WS token every ~55s and reconnects with
 * exponential backoff up to 30s.
 */
export function useWebSocket<T = unknown>(
  options: UseWebSocketOptions = {},
): { lastMessage: T | null; status: WsStatus } {
  const { enabled = true } = options;
  const [status, setLocalStatus] = useState<WsStatus>("offline");
  const [lastMessage, setLastMessage] = useState<unknown>(null);

  useEffect(() => {
    if (!enabled) return;
    setLocalStatus(state.status);
    setLastMessage(state.lastMessage);
    state.refCount += 1;
    const unsub = subscribe((s, m) => {
      setLocalStatus(s);
      setLastMessage(m);
    });
    if (state.refCount === 1 || !state.ws) {
      void connect();
    }
    return () => {
      unsub();
      state.refCount = Math.max(0, state.refCount - 1);
      if (state.refCount === 0) {
        disconnect();
      }
    };
  }, [enabled]);

  return { lastMessage: lastMessage as T | null, status };
}

/**
 * Thin wrapper that returns only the connection status. Used by the header
 * LiveIndicator. Internally shares the same singleton socket.
 */
export function useWebsocketStatus(): WsStatus {
  return useWebSocket({ enabled: true }).status;
}
