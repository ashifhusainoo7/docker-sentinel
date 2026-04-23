import { Shimmer } from "@/components/ui/motion/shimmer";
import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return <Shimmer className={cn("h-4 w-full rounded-md", className)} />;
}

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Shimmer
          key={i}
          className="h-3 rounded"
          {...(i === lines - 1 ? { style: { width: "70%" } } : {})}
        />
      ))}
    </div>
  );
}

export function SkeletonMetric() {
  return (
    <div className="space-y-3">
      <Shimmer className="h-3 w-24 rounded" />
      <Shimmer className="h-8 w-32 rounded" />
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border/50 bg-card/60 p-6 backdrop-blur">
      <Shimmer className="mb-4 h-5 w-40 rounded" />
      <SkeletonText lines={3} />
    </div>
  );
}

export function SkeletonTableRow({ cols = 6 }: { cols?: number }) {
  return (
    <div className="flex items-center gap-4 border-b border-border/30 px-4 py-3">
      {Array.from({ length: cols }).map((_, i) => (
        <Shimmer key={i} className="h-4 flex-1 rounded" />
      ))}
    </div>
  );
}
