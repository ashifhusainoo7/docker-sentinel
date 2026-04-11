"use client";

import { useEffect, useRef, useState } from "react";
import { getAccessToken } from "@/lib/auth";

const WS_URL = process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") || "ws://localhost:8000";

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const [lastEvent, setLastEvent] = useState<unknown>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;

    const socket = new WebSocket(`${WS_URL}/api/v1/ws/live?token=${token}`);

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        setLastEvent(JSON.parse(event.data));
      } catch {
        // Ignore non-JSON messages
      }
    };

    ws.current = socket;

    return () => {
      socket.close();
    };
  }, []);

  return { lastEvent, connected };
}
