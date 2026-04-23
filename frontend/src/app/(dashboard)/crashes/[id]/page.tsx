"use client";

import { use, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { format, formatDistanceToNow, parseISO } from "date-fns";
import { toast } from "sonner";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Copy,
  Flame,
  Info,
  Lightbulb,
  RefreshCw,
  Sparkles,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { GlowCard } from "@/components/ui/motion/glow-card";
import { AnimatedGradient } from "@/components/ui/motion/animated-gradient";
import { PulseDot } from "@/components/ui/motion/pulse-dot";
import { Skeleton, SkeletonText } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCrash } from "@/hooks/use-crash";
import type { CrashEvent } from "@/hooks/use-crashes";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function severityColor(sev: string | null): string {
  switch ((sev ?? "").toLowerCase()) {
    case "critical":
      return "var(--color-severity-critical)";
    case "high":
      return "var(--color-severity-high)";
    case "medium":
      return "var(--color-severity-medium)";
    case "low":
      return "var(--color-severity-low)";
    default:
      return "var(--color-muted-foreground)";
  }
}

function SeverityChip({ severity }: { severity: string | null }) {
  const sev = (severity ?? "unknown").toLowerCase();
  const Icon =
    sev === "critical"
      ? Flame
      : sev === "high"
        ? AlertTriangle
        : sev === "medium"
          ? AlertCircle
          : sev === "low"
            ? Info
            : AlertCircle;
  const color = severityColor(severity);
  const label = sev.charAt(0).toUpperCase() + sev.slice(1);

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{
        color,
        backgroundColor: `color-mix(in oklab, ${color} 20%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in oklab, ${color} 35%, transparent)`,
      }}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      {label}
    </span>
  );
}

function shortId(id: string | null | undefined, chars = 8): string {
  if (!id) return "—";
  return id.length > chars ? id.slice(0, chars) : id;
}

function formatIso(iso: string | null): string {
  if (!iso) return "—";
  try {
    return format(parseISO(iso), "yyyy-MM-dd HH:mm:ss");
  } catch {
    return iso;
  }
}

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Metadata sidecar
// ---------------------------------------------------------------------------

function MetadataRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-border/30 py-2 last:border-b-0">
      <span className="text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className="text-right font-mono text-sm tabular-nums text-foreground">
        {value}
      </span>
    </div>
  );
}

function MetadataSidecar({ crash }: { crash: CrashEvent }) {
  return (
    <GlowCard tint="cyan" className="w-full p-5 lg:w-80 lg:shrink-0">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Metadata
        </h3>
        <Sparkles className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
      </div>
      <div className="space-y-0">
        <MetadataRow label="ID" value={shortId(crash.id)} />
        <MetadataRow label="Container ID" value={shortId(crash.container_id, 12)} />
        <MetadataRow
          label="Exit Code"
          value={crash.exit_code ?? <span className="text-muted-foreground">—</span>}
        />
        <MetadataRow label="Host ID" value={shortId(crash.docker_host_id)} />
        <MetadataRow
          label="LLM Provider"
          value={
            crash.llm_provider ?? <span className="text-muted-foreground">—</span>
          }
        />
        <MetadataRow
          label="LLM Latency"
          value={
            crash.llm_latency_ms !== null ? (
              `${crash.llm_latency_ms}ms`
            ) : (
              <span className="text-muted-foreground">—</span>
            )
          }
        />
        <MetadataRow
          label="Restart Attempted"
          value={crash.restart_attempted ? "yes" : "no"}
        />
        <MetadataRow label="Slack Sent" value={crash.slack_sent ? "yes" : "no"} />
        <MetadataRow label="Email Sent" value={crash.email_sent ? "yes" : "no"} />
        <MetadataRow label="Call Made" value={crash.call_made ? "yes" : "no"} />
        <MetadataRow
          label="Created At"
          value={<span className="text-xs">{formatIso(crash.created_at)}</span>}
        />
        <MetadataRow
          label="Resolved At"
          value={
            crash.resolved_at ? (
              <span className="text-xs">{formatIso(crash.resolved_at)}</span>
            ) : (
              <span className="text-muted-foreground">—</span>
            )
          }
        />
      </div>
    </GlowCard>
  );
}

// ---------------------------------------------------------------------------
// Tab: Logs
// ---------------------------------------------------------------------------

function LogsTab({ crash }: { crash: CrashEvent }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(crash.logs ?? "");
      toast.success("Logs copied");
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Copy failed");
    }
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={onCopy}
        disabled={!crash.logs}
        className="absolute right-2 top-2 z-10 inline-flex items-center gap-1 rounded-md border border-border/50 bg-card/80 px-2 py-1 text-xs text-muted-foreground backdrop-blur transition-colors hover:text-foreground disabled:opacity-40"
      >
        {copied ? (
          <>
            <CheckCircle2 className="h-3 w-3" />
            Copied
          </>
        ) : (
          <>
            <Copy className="h-3 w-3" />
            Copy
          </>
        )}
      </button>
      <pre className="max-h-[500px] overflow-auto whitespace-pre-wrap rounded-xl border border-border/50 bg-neutral-950 p-4 font-mono text-xs text-neutral-200">
        {crash.logs || "No logs captured."}
      </pre>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: AI Analysis
// ---------------------------------------------------------------------------

function AnalysisTab({ crash }: { crash: CrashEvent }) {
  const confidencePct = Math.max(
    0,
    Math.min(100, Math.round((crash.confidence ?? 0) * 100)),
  );

  return (
    <div className="space-y-4">
      {crash.cache_hit && (
        <div className="inline-flex items-center gap-1.5 rounded-full border border-[color-mix(in_oklab,var(--color-accent-cyan)_35%,transparent)] bg-[color-mix(in_oklab,var(--color-accent-cyan)_15%,transparent)] px-2.5 py-1 text-xs font-medium text-[var(--color-accent-cyan)]">
          <Sparkles className="h-3 w-3" />
          Cached analysis — no LLM call was made
        </div>
      )}

      <GlowCard tint="violet" className="p-6">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Root Cause
        </h4>
        <p className="mb-5 text-sm leading-relaxed text-foreground">
          {crash.root_cause || (
            <span className="text-muted-foreground">No root cause analysis.</span>
          )}
        </p>

        {crash.confidence !== null && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="uppercase tracking-wider">Confidence</span>
              <span className="font-mono tabular-nums text-foreground">
                {confidencePct}%
              </span>
            </div>
            <div className="relative h-2 overflow-hidden rounded-full bg-muted/40">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${confidencePct}%` }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-cyan-400 to-violet-500"
              />
            </div>
          </div>
        )}
      </GlowCard>

      {crash.suggestions.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Suggestions
          </h4>
          {crash.suggestions.map((suggestion, idx) => (
            <div
              key={idx}
              className="flex gap-3 rounded-xl border border-border/50 bg-card/60 p-4 backdrop-blur"
            >
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[color-mix(in_oklab,var(--color-accent-violet)_15%,transparent)] text-[var(--color-accent-violet)]">
                <Lightbulb className="h-3.5 w-3.5" aria-hidden="true" />
              </div>
              <div className="flex-1 space-y-1">
                <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Suggestion {idx + 1}
                </div>
                <p className="text-sm leading-relaxed">{suggestion}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {crash.suggestions.length === 0 && !crash.root_cause && (
        <EmptyState
          icon={<Sparkles />}
          title="No analysis available"
          description="The AI agent has not produced a root-cause analysis for this event."
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Timeline
// ---------------------------------------------------------------------------

interface TimelineStep {
  label: string;
  description?: string;
  timestamp: string | null;
  complete: boolean;
  tint: "cyan" | "violet" | "amber" | "rose" | "emerald" | "muted";
}

function TimelineTab({ crash }: { crash: CrashEvent }) {
  let analysisTs: string | null = null;
  if (crash.llm_latency_ms !== null) {
    try {
      const base = parseISO(crash.created_at).getTime();
      analysisTs = new Date(base + crash.llm_latency_ms).toISOString();
    } catch {
      analysisTs = null;
    }
  }

  const steps: TimelineStep[] = [
    {
      label: "Container crashed",
      description: `${crash.container_name} exited${crash.exit_code !== null ? ` with code ${crash.exit_code}` : ""}.`,
      timestamp: crash.created_at,
      complete: true,
      tint: "rose",
    },
    {
      label: "Analysis received",
      description: crash.cache_hit
        ? "Cached analysis served — no LLM call."
        : crash.llm_provider
          ? `${crash.llm_provider} responded in ${crash.llm_latency_ms ?? "?"}ms.`
          : "No analysis recorded.",
      timestamp: analysisTs,
      complete: crash.root_cause !== null || crash.cache_hit,
      tint: "violet",
    },
    {
      label: "Restart attempted",
      description: crash.restart_attempted
        ? crash.restart_success === true
          ? "Container restarted successfully."
          : crash.restart_success === false
            ? "Restart attempt failed."
            : "Restart in progress…"
        : "No restart attempted.",
      timestamp: crash.restart_attempted ? crash.created_at : null,
      complete: crash.restart_attempted,
      tint: crash.restart_success === false ? "rose" : "amber",
    },
    {
      label: "Notifications sent",
      description: [
        crash.slack_sent ? "Slack" : null,
        crash.email_sent ? "Email" : null,
        crash.call_made ? "Call" : null,
      ]
        .filter(Boolean)
        .join(", ") || "No notifications sent.",
      timestamp: null,
      complete: crash.slack_sent || crash.email_sent || crash.call_made,
      tint: "cyan",
    },
    {
      label: "Resolved",
      description: crash.resolved_at
        ? "Event marked as resolved."
        : "Event is still open.",
      timestamp: crash.resolved_at,
      complete: crash.resolved_at !== null,
      tint: "emerald",
    },
  ];

  const tintMap: Record<TimelineStep["tint"], string> = {
    cyan: "var(--color-accent-cyan)",
    violet: "var(--color-accent-violet)",
    amber: "oklch(0.80 0.15 75)",
    rose: "oklch(0.65 0.22 20)",
    emerald: "oklch(0.72 0.18 155)",
    muted: "var(--color-muted-foreground)",
  };

  return (
    <div className="relative">
      <div className="space-y-6">
        {steps.map((step, idx) => {
          const color = step.complete ? tintMap[step.tint] : "var(--color-muted)";
          return (
            <div key={idx} className="relative flex gap-4">
              {/* Connector line */}
              {idx < steps.length - 1 && (
                <span
                  className="absolute left-[11px] top-6 h-full w-px"
                  style={{ backgroundColor: "var(--color-border)" }}
                  aria-hidden="true"
                />
              )}
              {/* Dot */}
              <span
                className="relative z-10 mt-1 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
                style={{
                  backgroundColor: `color-mix(in oklab, ${color} 20%, transparent)`,
                  boxShadow: `inset 0 0 0 1px ${color}`,
                }}
                aria-hidden="true"
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: color }}
                />
              </span>
              <div className="flex-1 pb-2">
                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      "text-sm font-semibold",
                      !step.complete && "text-muted-foreground",
                    )}
                  >
                    {step.label}
                  </span>
                  {step.timestamp && (
                    <span className="font-mono text-xs tabular-nums text-muted-foreground">
                      {formatIso(step.timestamp)}
                    </span>
                  )}
                </div>
                {step.description && (
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {step.description}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Actions
// ---------------------------------------------------------------------------

function ActionsTab() {
  return (
    <div className="space-y-4">
      <EmptyState
        variant="coming-soon"
        title="Agent actions"
        description="Manual intervention buttons will ship in the next release."
      />
      <div className="flex flex-wrap gap-3">
        <Button variant="outline" disabled title="Coming soon">
          <RefreshCw className="mr-2 h-4 w-4" />
          Trigger Restart
        </Button>
        <Button variant="outline" disabled title="Coming soon">
          <CheckCircle2 className="mr-2 h-4 w-4" />
          Mark Resolved
        </Button>
        <Button variant="destructive" disabled title="Coming soon">
          <Trash2 className="mr-2 h-4 w-4" />
          Delete Event
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hero
// ---------------------------------------------------------------------------

function Hero({ crash }: { crash: CrashEvent }) {
  return (
    <motion.div
      layoutId={`crash-${crash.id}`}
      className="rounded-2xl border border-border/50 bg-card/60 p-6 backdrop-blur"
    >
      <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-mono text-3xl font-bold tracking-tight text-foreground">
            {crash.container_name}
          </h1>
          <p className="mt-1 truncate font-mono text-sm text-muted-foreground">
            {crash.image}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <SeverityChip severity={crash.severity} />
            {crash.category && (
              <span className="inline-flex items-center rounded-full border border-border/60 px-2 py-0.5 text-xs font-medium text-muted-foreground">
                {crash.category}
              </span>
            )}
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              Crashed {timeAgo(crash.created_at)}
            </span>
          </div>
        </div>

        <div className="shrink-0">
          {crash.resolved_at ? (
            <div className="flex items-center gap-2 rounded-full bg-emerald-400/10 px-3 py-1.5 text-sm font-medium text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              <span>
                Resolved{" "}
                <span className="font-mono text-xs tabular-nums text-emerald-400/80">
                  {formatIso(crash.resolved_at)}
                </span>
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-full bg-rose-400/10 px-3 py-1.5 text-sm font-medium text-rose-400">
              <PulseDot state="offline" />
              <span>Open</span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <div className="rounded-2xl border border-border/50 bg-card/60 p-6 backdrop-blur">
        <Skeleton className="mb-3 h-9 w-2/3" />
        <Skeleton className="mb-4 h-4 w-1/3" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
      </div>
      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="flex-1 space-y-4">
          <Skeleton className="h-9 w-full rounded-lg" />
          <SkeletonText lines={6} />
        </div>
        <div className="w-full lg:w-80">
          <div className="rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur">
            <SkeletonText lines={10} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CrashDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { crash, loading, error } = useCrash(id);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <Link
        href="/crashes"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All crashes
      </Link>

      {loading && !crash ? (
        <DetailSkeleton />
      ) : error || !crash ? (
        <EmptyState
          icon={<AlertTriangle />}
          title="Crash not found"
          description={
            error?.message ??
            "This event may have been deleted, or the ID is invalid."
          }
          action={
            <Button render={<Link href="/crashes" />}>Back to list</Button>
          }
        />
      ) : (
        <>
          <Hero crash={crash} />

          <div className="flex flex-col gap-6 lg:flex-row">
            {/* Main (tabs) */}
            <div className="min-w-0 flex-1">
              <Tabs defaultValue="logs">
                <TabsList>
                  <TabsTrigger value="logs">Logs</TabsTrigger>
                  <TabsTrigger value="analysis">
                    <AnimatedGradient>AI</AnimatedGradient>
                    <span>&nbsp;Analysis</span>
                  </TabsTrigger>
                  <TabsTrigger value="timeline">Timeline</TabsTrigger>
                  <TabsTrigger value="actions">Actions</TabsTrigger>
                </TabsList>
                <TabsContent value="logs" className="pt-4">
                  <LogsTab crash={crash} />
                </TabsContent>
                <TabsContent value="analysis" className="pt-4">
                  <AnalysisTab crash={crash} />
                </TabsContent>
                <TabsContent value="timeline" className="pt-4">
                  <TimelineTab crash={crash} />
                </TabsContent>
                <TabsContent value="actions" className="pt-4">
                  <ActionsTab />
                </TabsContent>
              </Tabs>
            </div>

            {/* Sidecar */}
            <MetadataSidecar crash={crash} />
          </div>
        </>
      )}
    </motion.div>
  );
}
