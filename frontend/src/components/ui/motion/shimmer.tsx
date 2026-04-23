"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ShimmerProps {
  className?: string;
}

/**
 * Animated gradient sweep for skeleton loading states.
 * Usage:  <Shimmer className="h-4 w-32 rounded" />
 */
export function Shimmer({ className }: ShimmerProps) {
  return (
    <motion.div
      className={cn(
        "relative overflow-hidden rounded-md bg-muted/40",
        className,
      )}
      aria-hidden="true"
    >
      <motion.div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, oklch(1 0 0 / 0.08) 50%, transparent 100%)",
        }}
        animate={{ x: ["-100%", "100%"] }}
        transition={{
          duration: 1.8,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
    </motion.div>
  );
}
