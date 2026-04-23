import { SkeletonCard } from "@/components/ui/skeleton";
import { Shimmer } from "@/components/ui/motion/shimmer";

/**
 * Loading skeleton for the settings hub. Mirrors the 2-column grid of
 * section cards so the shell doesn't jump when the page resolves.
 */
export default function SettingsLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Shimmer className="h-7 w-40 rounded" />
        <Shimmer className="h-4 w-72 rounded" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
}
