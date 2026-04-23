"use client";

import { PulseDot, type PulseDotState } from "@/components/ui/motion/pulse-dot";
import { cn } from "@/lib/utils";

interface LiveIndicatorProps {
  state: PulseDotState;
  className?: string;
  showLabel?: boolean;
}

const labelMap: Record<PulseDotState, string> = {
  live: "Live",
  connecting: "Reconnecting",
  offline: "Offline",
};

export function LiveIndicator({ state, className, showLabel = true }: LiveIndicatorProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-xs text-muted-foreground", className)}>
      <PulseDot state={state} />
      {showLabel && <span className="uppercase tracking-wider">{labelMap[state]}</span>}
    </span>
  );
}
