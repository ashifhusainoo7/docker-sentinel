"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface AnimatedGradientProps {
  children: ReactNode;
  className?: string;
  /** Animation speed in seconds for a full cycle. Default 6s. */
  duration?: number;
}

/**
 * Text with an animated brand gradient (cyan → violet → magenta → cyan).
 * Use for brand wordmarks and hero display text.
 *
 * Usage:  <AnimatedGradient className="text-4xl font-bold">DockerSentinel</AnimatedGradient>
 */
export function AnimatedGradient({ children, className, duration = 6 }: AnimatedGradientProps) {
  return (
    <motion.span
      className={cn("bg-clip-text text-transparent", className)}
      style={{
        backgroundImage:
          "linear-gradient(90deg, oklch(0.72 0.15 205), oklch(0.62 0.20 290), oklch(0.65 0.25 340), oklch(0.72 0.15 205))",
        backgroundSize: "200% 100%",
      }}
      animate={{ backgroundPosition: ["0% 50%", "200% 50%"] }}
      transition={{ duration, repeat: Infinity, ease: "linear" }}
    >
      {children}
    </motion.span>
  );
}
