"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export type PulseDotState = "live" | "connecting" | "offline";

interface PulseDotProps {
  state: PulseDotState;
  className?: string;
  label?: string;
}

const stateConfig = {
  live: {
    color: "oklch(0.75 0.18 155)", // green
    ariaLabel: "Live",
  },
  connecting: {
    color: "oklch(0.80 0.15 75)", // amber
    ariaLabel: "Connecting",
  },
  offline: {
    color: "oklch(0.62 0.25 15)", // red
    ariaLabel: "Offline",
  },
} as const;

/**
 * Small status dot with state-driven animation.
 * - live: green, pulsing outward ripple
 * - connecting: amber, spinning orbital ring
 * - offline: red, static
 */
export function PulseDot({ state, className, label }: PulseDotProps) {
  const { color, ariaLabel } = stateConfig[state];

  return (
    <span
      className={cn("relative inline-flex h-2.5 w-2.5 items-center justify-center", className)}
      role="status"
      aria-label={label ?? ariaLabel}
    >
      {/* Core dot */}
      <span
        className="relative z-10 h-2.5 w-2.5 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
      />

      {/* State-specific animation layer */}
      {state === "live" && (
        <motion.span
          className="absolute inset-0 rounded-full"
          style={{ backgroundColor: color }}
          initial={{ scale: 1, opacity: 0.6 }}
          animate={{ scale: 2.4, opacity: 0 }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut" }}
          aria-hidden="true"
        />
      )}

      {state === "connecting" && (
        <motion.span
          className="absolute inset-[-4px] rounded-full border-2"
          style={{ borderColor: color, borderTopColor: "transparent" }}
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          aria-hidden="true"
        />
      )}
    </span>
  );
}
