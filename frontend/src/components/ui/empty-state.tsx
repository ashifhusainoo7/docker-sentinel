import { cn } from "@/lib/utils";
import { AnimatedGradient } from "@/components/ui/motion/animated-gradient";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  variant?: "default" | "coming-soon";
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  variant = "default",
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border/50 p-12 text-center",
        className,
      )}
    >
      {variant === "coming-soon" && (
        <div className="mb-2">
          <AnimatedGradient className="text-xs font-semibold uppercase tracking-widest">
            Coming Soon
          </AnimatedGradient>
        </div>
      )}
      {icon && <div className="text-muted-foreground [&_svg]:h-10 [&_svg]:w-10">{icon}</div>}
      <div className="space-y-1">
        <h3 className="text-lg font-semibold">{title}</h3>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
