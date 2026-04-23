"use client";

import { useEffect } from "react";
import { AlertOctagon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * App-router global error boundary. Next.js renders this whenever a server
 * component or unhandled client error bubbles up. Keep it dependency-free so
 * it can still render even when the dashboard shell is broken.
 */
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    // Surface to the browser console so the digest is discoverable during
    // development. Production crashes still propagate to Next.js telemetry.
    console.error("Unhandled app error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-lg">
        <EmptyState
          icon={<AlertOctagon />}
          title="Something went wrong"
          description={error.message || "An unexpected error occurred."}
          action={<Button onClick={reset}>Try again</Button>}
        />
      </div>
    </div>
  );
}
