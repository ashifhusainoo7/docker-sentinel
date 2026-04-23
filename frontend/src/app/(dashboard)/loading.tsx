import { SkeletonCard, SkeletonMetric } from "@/components/ui/skeleton";
import { Shimmer } from "@/components/ui/motion/shimmer";

export default function DashboardLoading() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Shimmer className="h-8 w-40 rounded" />
        <Shimmer className="h-9 w-56 rounded-full" />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="rounded-xl border border-border/50 bg-card/60 p-6 backdrop-blur"
          >
            <SkeletonMetric />
          </div>
        ))}
      </div>

      <SkeletonCard />

      <div className="rounded-xl border border-border/50 bg-card/60 p-6 backdrop-blur">
        <Shimmer className="mb-4 h-5 w-40 rounded" />
        <Shimmer className="h-[280px] w-full rounded-md" />
      </div>
    </div>
  );
}
