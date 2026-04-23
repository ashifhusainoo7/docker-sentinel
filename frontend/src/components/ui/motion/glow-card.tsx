"use client";

import { useRef, type ComponentProps, type MouseEvent } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type GlowCardProps = ComponentProps<typeof Card> & {
  /** Glow color — defaults to cyan; pass "violet" for variants. */
  tint?: "cyan" | "violet" | "magenta";
};

const tintMap = {
  cyan: "oklch(0.72 0.15 205 / 0.22)",
  violet: "oklch(0.62 0.20 290 / 0.22)",
  magenta: "oklch(0.65 0.25 340 / 0.22)",
} as const;

/**
 * Card with a hover radial-glow that follows the cursor.
 * Wraps Shadcn <Card> — accepts all Card props.
 *
 * Usage:  <GlowCard tint="violet"><CardHeader>...</CardHeader></GlowCard>
 */
export function GlowCard({ tint = "cyan", className, children, ...props }: GlowCardProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  const onMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--glow-x", `${e.clientX - rect.left}px`);
    el.style.setProperty("--glow-y", `${e.clientY - rect.top}px`);
  };

  return (
    <Card
      ref={ref}
      onMouseMove={onMouseMove}
      className={cn(
        "group/glow relative overflow-hidden transition-colors",
        "before:pointer-events-none before:absolute before:inset-0 before:z-0 before:opacity-0 before:transition-opacity before:duration-300",
        "hover:before:opacity-100",
        className,
      )}
      style={{
        // CSS variable consumed by the ::before pseudo-element
        ["--glow-color" as string]: tintMap[tint],
        // Pseudo-element needs its own style — use a class instead:
      }}
      {...props}
    >
      {/* Radial spotlight layer */}
      <div
        className="pointer-events-none absolute inset-0 z-0 opacity-0 transition-opacity duration-300 group-hover/glow:opacity-100"
        style={{
          background: `radial-gradient(600px circle at var(--glow-x, 50%) var(--glow-y, 50%), ${tintMap[tint]}, transparent 40%)`,
        }}
        aria-hidden="true"
      />
      <div className="relative z-10">{children}</div>
    </Card>
  );
}
