"use client";

import { useEffect, useMemo, useState } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  type MotionValue,
} from "framer-motion";
import { format, parseISO } from "date-fns";
import {
  Activity,
  ArrowDown,
  ArrowUp,
  Flame,
  RefreshCw,
  ServerCog,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { GlowCard } from "@/components/ui/motion/glow-card";
import { AnimatedGradient } from "@/components/ui/motion/animated-gradient";
import { SkeletonMetric, SkeletonText, Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  useDashboardSummary,
  useDashboardMetrics,
  useDashboardTimeline,
  type Period,
} from "@/hooks/use-dashboard";

const PERIODS: Period[] = ["24h", "7d", "30d"];

// ---------------------------------------------------------------------------
// Count-up number
// ---------------------------------------------------------------------------

interface AnimatedNumberProps {
  value: number;
  format?: (v: number) => string;
  className?: string;
}

function AnimatedNumber({ value, format: formatFn, className }: AnimatedNumberProps) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 100, damping: 30 });
  const rounded: MotionValue<string> = useTransform(spring, (latest) =>
    formatFn ? formatFn(latest) : Math.round(latest).toLocaleString(),
  );

  useEffect(() => {
    motionValue.set(value);
  }, [motionValue, value]);

  return <motion.span className={className}>{rounded}</motion.span>;
}

// ---------------------------------------------------------------------------
// Delta indicator pill
// ---------------------------------------------------------------------------

interface DeltaPillProps {
  deltaPct: number | null | undefined;
  /** When true, a positive delta is GOOD (green). Default false (positive = bad/red). */
  inverse?: boolean;
}

function DeltaPill({ deltaPct, inverse = false }: DeltaPillProps) {
  if (deltaPct === null || deltaPct === undefined) return null;
  const up = deltaPct > 0;
  const down = deltaPct < 0;
  const isGood = inverse ? up : down;
  const isBad = inverse ? down : up;

  const colorClass = isGood
    ? "text-emerald-400 bg-emerald-400/10"
    : isBad
      ? "text-rose-400 bg-rose-400/10"
      : "text-muted-foreground bg-muted/40";

  const Icon = up ? ArrowUp : down ? ArrowDown : null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium tabular-nums",
        colorClass,
      )}
    >
      {Icon ? <Icon className="h-3 w-3" aria-hidden="true" /> : null}
      {Math.abs(deltaPct).toFixed(1)}%
    </span>
  );
}

// ---------------------------------------------------------------------------
// Metric tile
// ---------------------------------------------------------------------------

interface MetricTileProps {
  label: string;
  value: number | null;
  format?: (v: number) => string;
  tint: "cyan" | "violet" | "magenta";
  icon: React.ReactNode;
  deltaPct?: number | null;
  deltaInverse?: boolean;
  loading?: boolean;
  index: number;
}

function MetricTile({
  label,
  value,
  format: formatFn,
  tint,
  icon,
  deltaPct,
  deltaInverse,
  loading,
  index,
}: MetricTileProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06 }}
    >
      <GlowCard tint={tint} className="p-6">
        {loading || value === null ? (
          <SkeletonMetric />
        ) : (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                {label}
              </span>
              <span className="text-muted-foreground/70 [&_svg]:h-4 [&_svg]:w-4">
                {icon}
              </span>
            </div>
            <AnimatedNumber
              value={value}
              format={formatFn}
              className="font-mono text-4xl font-bold tracking-tight tabular-nums"
            />
            {deltaPct !== undefined && deltaPct !== null ? (
              <DeltaPill deltaPct={deltaPct} inverse={deltaInverse} />
            ) : null}
          </div>
        )}
      </GlowCard>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Period selector (shared-element glow)
// ---------------------------------------------------------------------------

interface PeriodSelectorProps {
  value: Period;
  onChange: (p: Period) => void;
}

function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  return (
    <div className="flex gap-1 rounded-full border border-border/50 bg-card/60 p-1 backdrop-blur">
      {PERIODS.map((p) => {
        const active = value === p;
        return (
          <button
            key={p}
            type="button"
            onClick={() => onChange(p)}
            className={cn(
              "relative rounded-full px-4 py-1.5 text-xs font-medium transition-colors",
              active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {active ? (
              <motion.div
                layoutId="period-active"
                className="absolute inset-0 -z-0 rounded-full bg-gradient-to-r from-cyan-400/20 to-violet-500/20 ring-1 ring-cyan-400/40"
                style={{ boxShadow: "var(--shadow-glow-cyan)" }}
                transition={{ type: "spring", stiffness: 380, damping: 30 }}
              />
            ) : null}
            <span className="relative z-10 uppercase tracking-wider">{p}</span>
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chart tooltip (glass)
// ---------------------------------------------------------------------------

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    dataKey?: string | number;
    value?: number | string;
    color?: string;
  }>;
  label?: string | number;
  bucket: "hour" | "day";
}

function ChartTooltip({ active, payload, label, bucket }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0 || label === undefined) return null;
  let labelText = String(label);
  try {
    labelText = format(
      parseISO(String(label)),
      bucket === "hour" ? "MMM d, HH:mm" : "MMM d, yyyy",
    );
  } catch {
    // fall back to raw label
  }

  return (
    <div className="rounded-lg border border-border/50 bg-card/90 p-3 shadow-lg backdrop-blur">
      <p className="mb-1.5 text-xs font-medium text-muted-foreground">{labelText}</p>
      <div className="space-y-1">
        {payload.map((entry) => (
          <div key={String(entry.dataKey)} className="flex items-center gap-2 text-xs">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: entry.color }}
              aria-hidden="true"
            />
            <span className="capitalize text-muted-foreground">
              {String(entry.dataKey)}
            </span>
            <span className="ml-auto font-mono font-semibold tabular-nums">
              {entry.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [period, setPeriod] = useState<Period>("24h");

  const summary = useDashboardSummary();
  const metrics = useDashboardMetrics(period);
  const timeline = useDashboardTimeline(period);

  const timelineData = useMemo(() => timeline.data?.points ?? [], [timeline.data]);
  const bucket = timeline.data?.bucket ?? "hour";

  const timelineEmpty = useMemo(() => {
    if (!timeline.data) return false;
    if (timelineData.length === 0) return true;
    return timelineData.every((p) => p.crashes === 0 && p.restarts === 0);
  }, [timeline.data, timelineData]);

  const aiSummaryText = useMemo(() => {
    if (!summary.data || !metrics.data) return null;
    const crashes = metrics.data.crashes_total;
    const hosts = summary.data.active_hosts;
    const restarts = summary.data.restarts_24h;
    const hitRate = summary.data.cache_hit_rate;
    const saved = Math.round(hitRate * crashes);
    return `In the last ${period}, your fleet experienced ${crashes} crashes across ${hosts} active hosts. Auto-restart resolved ${restarts} of them. Cache hit rate is ${(hitRate * 100).toFixed(1)}% — saving approximately ${saved} LLM calls.`;
  }, [summary.data, metrics.data, period]);

  // --- Error state (summary failed) -------------------------------------
  if (summary.error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Dashboard</h2>
        </div>
        <EmptyState
          icon={<Activity />}
          title="Could not load dashboard"
          description={summary.error.message}
          action={
            <Button
              variant="outline"
              onClick={() => {
                if (typeof window !== "undefined") window.location.reload();
              }}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {/* Metric tiles */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricTile
          index={0}
          label={period === "24h" ? "Crashes (24h)" : `Crashes (${period})`}
          value={
            period === "24h"
              ? (summary.data?.crashes_24h ?? null)
              : (metrics.data?.crashes_total ?? null)
          }
          tint="cyan"
          icon={<Flame />}
          deltaPct={metrics.data?.crashes_delta_pct ?? null}
          deltaInverse={false}
          loading={period === "24h" ? summary.loading : summary.loading || metrics.loading}
        />
        <MetricTile
          index={1}
          label="Auto-Restarts (24h)"
          value={summary.data?.restarts_24h ?? null}
          tint="violet"
          icon={<RefreshCw />}
          loading={summary.loading}
        />
        <MetricTile
          index={2}
          label="Cache Hit Rate"
          value={summary.data ? summary.data.cache_hit_rate * 100 : null}
          format={(v) => `${v.toFixed(1)}%`}
          tint="magenta"
          icon={<Zap />}
          deltaInverse
          loading={summary.loading}
        />
        <MetricTile
          index={3}
          label="Active Hosts"
          value={summary.data?.active_hosts ?? null}
          tint="cyan"
          icon={<ServerCog />}
          loading={summary.loading}
        />
      </div>

      {/* AI Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 4 * 0.06 }}
      >
        <GlowCard tint="cyan" className="p-0">
          <div className="flex gap-4 p-6">
            <div
              aria-hidden="true"
              className="w-1 shrink-0 rounded-full bg-gradient-to-b from-cyan-400 to-violet-500"
            />
            <div className="flex-1 space-y-2">
              <h3 className="text-lg font-semibold">
                <AnimatedGradient className="font-bold">AI</AnimatedGradient>{" "}
                <span>Summary</span>
              </h3>
              {summary.loading || metrics.loading ? (
                <SkeletonText lines={3} />
              ) : metrics.error ? (
                <p className="text-sm text-muted-foreground">
                  AI summary unavailable — {metrics.error.message}
                </p>
              ) : aiSummaryText ? (
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {aiSummaryText}
                </p>
              ) : (
                <SkeletonText lines={3} />
              )}
            </div>
          </div>
        </GlowCard>
      </motion.div>

      {/* Crash Timeline */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 5 * 0.06 }}
      >
        <GlowCard tint="violet" className="p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold">Crash Timeline</h3>
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground tabular-nums">
              {period}
            </span>
          </div>

          {timeline.loading ? (
            <div className="space-y-3">
              <Skeleton className="h-[280px] w-full rounded-md" />
            </div>
          ) : timeline.error ? (
            <EmptyState
              icon={<Activity />}
              title="Could not load timeline"
              description={timeline.error.message}
            />
          ) : timelineEmpty ? (
            <EmptyState
              icon={<Activity />}
              title="No activity yet"
              description="Once your monitored hosts start reporting crashes, the timeline will populate here."
            />
          ) : (
            <div className="relative">
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart
                  data={timelineData}
                  margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="fill-crashes" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor="oklch(0.72 0.15 205)"
                        stopOpacity={0.4}
                      />
                      <stop
                        offset="100%"
                        stopColor="oklch(0.72 0.15 205)"
                        stopOpacity={0}
                      />
                    </linearGradient>
                    <linearGradient id="fill-restarts" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor="oklch(0.62 0.20 290)"
                        stopOpacity={0.4}
                      />
                      <stop
                        offset="100%"
                        stopColor="oklch(0.62 0.20 290)"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="var(--color-border)"
                    strokeOpacity={0.3}
                  />
                  <XAxis
                    dataKey="t"
                    stroke="var(--color-muted-foreground)"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(t: string) => {
                      try {
                        return format(parseISO(t), bucket === "hour" ? "HH:mm" : "MMM d");
                      } catch {
                        return t;
                      }
                    }}
                  />
                  <YAxis
                    stroke="var(--color-muted-foreground)"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    content={(props: any) => {
                      return (
                        <ChartTooltip
                          active={props?.active}
                          payload={props?.payload}
                          label={props?.label}
                          bucket={bucket}
                        />
                      );
                    }}
                    cursor={{
                      stroke: "var(--color-border)",
                      strokeDasharray: "3 3",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="crashes"
                    stroke="oklch(0.72 0.15 205)"
                    strokeWidth={2}
                    fill="url(#fill-crashes)"
                    isAnimationActive
                    animationDuration={700}
                  />
                  <Area
                    type="monotone"
                    dataKey="restarts"
                    stroke="oklch(0.62 0.20 290)"
                    strokeWidth={2}
                    fill="url(#fill-restarts)"
                    isAnimationActive
                    animationDuration={700}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </GlowCard>
      </motion.div>
    </div>
  );
}
