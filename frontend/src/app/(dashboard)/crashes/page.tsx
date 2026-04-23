"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { formatDistanceToNow, parseISO } from "date-fns";
import {
  AlertCircle,
  AlertTriangle,
  Flame,
  Info,
  RefreshCw,
  Search,
  ShieldCheck,
  Zap,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { LiveIndicator } from "@/components/ui/live-indicator";
import { SkeletonTableRow } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCrashes, type CrashEvent } from "@/hooks/use-crashes";
import { useWebSocket } from "@/hooks/use-websocket";
import { cn } from "@/lib/utils";

const SEVERITY_OPTIONS = [
  { value: "", label: "All severities" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const CATEGORY_OPTIONS = [
  { value: "", label: "All categories" },
  { value: "oom", label: "OOM" },
  { value: "dependency_failure", label: "Dependency Failure" },
  { value: "config_error", label: "Config Error" },
  { value: "code_bug", label: "Code Bug" },
  { value: "network", label: "Network" },
  { value: "unknown", label: "Unknown" },
];

// ---------------------------------------------------------------------------
// Severity badge
// ---------------------------------------------------------------------------

interface SeverityBadgeProps {
  severity: string | null;
}

function SeverityBadge({ severity }: SeverityBadgeProps) {
  const sev = (severity ?? "unknown").toLowerCase();
  const config = {
    critical: {
      Icon: Flame,
      color: "var(--color-severity-critical)",
      label: "Critical",
    },
    high: {
      Icon: AlertTriangle,
      color: "var(--color-severity-high)",
      label: "High",
    },
    medium: {
      Icon: AlertCircle,
      color: "var(--color-severity-medium)",
      label: "Medium",
    },
    low: {
      Icon: Info,
      color: "var(--color-severity-low)",
      label: "Low",
    },
  }[sev];

  if (!config) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-border/50 bg-muted/40 px-2 py-0.5 text-xs font-medium text-muted-foreground">
        <AlertCircle className="h-3 w-3" />
        Unknown
      </span>
    );
  }

  const { Icon, color, label } = config;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
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

// ---------------------------------------------------------------------------
// Status pill (Open / Restarting / Resolved)
// ---------------------------------------------------------------------------

function StatusPill({ crash }: { crash: CrashEvent }) {
  if (crash.resolved_at) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-400/10 px-2 py-0.5 text-xs font-medium text-emerald-400">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        Resolved
      </span>
    );
  }
  if (crash.restart_attempted) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-400/10 px-2 py-0.5 text-xs font-medium text-amber-400">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
        Restarting
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-rose-400/10 px-2 py-0.5 text-xs font-medium text-rose-400">
      <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
      Open
    </span>
  );
}

// ---------------------------------------------------------------------------
// Filter select (native <select> styled to match Input look)
// ---------------------------------------------------------------------------

interface FilterSelectProps {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  ariaLabel: string;
}

function FilterSelect({ value, onChange, options, ariaLabel }: FilterSelectProps) {
  return (
    <select
      aria-label={ariaLabel}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-8 min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm text-foreground transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} className="bg-background">
          {opt.label}
        </option>
      ))}
    </select>
  );
}

// ---------------------------------------------------------------------------
// Severity token for flash background
// ---------------------------------------------------------------------------

function severityToken(sev: string | null): string {
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
      return "var(--color-muted)";
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CrashesPage() {
  const router = useRouter();
  const [severity, setSeverity] = useState<string>("");
  const [category, setCategory] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  // Flash-id tracking: new crashes arriving via WS highlight for ~1.4s.
  const [flashIds, setFlashIds] = useState<Set<string>>(() => new Set());
  // Per-id timer handles so rapid bursts of WS crashes don't cancel each
  // other's clear-timers (which would leave early rows permanently flashing).
  const flashTimersRef = useRef<Map<string, number>>(new Map());

  const { crashes, loading, error, refresh, prependCrash } = useCrashes({
    severity: severity || undefined,
    category: category || undefined,
    limit: 50,
  });

  const { lastMessage, status: wsStatus } = useWebSocket<{
    type: string;
    crash?: CrashEvent;
  }>({ enabled: true });

  useEffect(() => {
    if (lastMessage?.type !== "crash" || !lastMessage.crash) return;
    const c = lastMessage.crash;

    // Respect the active severity/category filters. Empty string is the
    // "all" sentinel (same semantics as the fetch call). Case-insensitive
    // compare to match the rest of the page's severity handling.
    const sevFilter = severity.toLowerCase();
    const catFilter = category.toLowerCase();
    const crashSev = (c.severity ?? "").toLowerCase();
    const crashCat = (c.category ?? "").toLowerCase();
    if (sevFilter && crashSev !== sevFilter) return;
    if (catFilter && crashCat !== catFilter) return;

    prependCrash(c);

    // Cancel any prior timer for this id (e.g. the same crash re-inserted).
    const timers = flashTimersRef.current;
    const existing = timers.get(c.id);
    if (existing !== undefined) {
      clearTimeout(existing);
    }

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setFlashIds((ids) => {
      const n = new Set(ids);
      n.add(c.id);
      return n;
    });

    const handle = window.setTimeout(() => {
      setFlashIds((ids) => {
        const n = new Set(ids);
        n.delete(c.id);
        return n;
      });
      flashTimersRef.current.delete(c.id);
    }, 1400);
    timers.set(c.id, handle);
  }, [lastMessage, prependCrash, severity, category]);

  // Clear all pending flash timers on unmount so we don't leak them or
  // setState on an unmounted component.
  useEffect(() => {
    const timers = flashTimersRef.current;
    return () => {
      for (const handle of timers.values()) {
        clearTimeout(handle);
      }
      timers.clear();
    };
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return crashes;
    return crashes.filter((c) => c.container_name.toLowerCase().includes(q));
  }, [crashes, search]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Crash Events</h2>
        <LiveIndicator state={wsStatus} />
      </div>

      {/* Filter bar */}
      <div className="flex flex-col gap-3 rounded-xl border border-border/50 bg-card/60 p-4 backdrop-blur sm:flex-row sm:items-center">
        <FilterSelect
          value={severity}
          onChange={setSeverity}
          options={SEVERITY_OPTIONS}
          ariaLabel="Filter by severity"
        />
        <FilterSelect
          value={category}
          onChange={setCategory}
          options={CATEGORY_OPTIONS}
          ariaLabel="Filter by category"
        />
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="text"
            placeholder="Search by container name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <Button variant="outline" size="sm" onClick={() => refresh()}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Content */}
      {loading && crashes.length === 0 ? (
        <div className="rounded-xl border border-border/50 bg-card/40 backdrop-blur">
          <div className="flex items-center gap-4 border-b border-border/30 bg-muted/20 px-4 py-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <span className="flex-1">Time</span>
            <span className="flex-1">Container</span>
            <span className="flex-1">Severity</span>
            <span className="flex-1">Category</span>
            <span className="flex-1">Exit</span>
            <span className="flex-1">Cache</span>
            <span className="flex-1">Status</span>
          </div>
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonTableRow key={i} cols={7} />
          ))}
        </div>
      ) : error ? (
        <EmptyState
          icon={<AlertTriangle />}
          title="Could not load crashes"
          description={error.message}
          action={
            <Button onClick={() => refresh()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          }
        />
      ) : crashes.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck />}
          title="All quiet on the container front"
          description="No crash events yet. As soon as a monitored host reports an event, it'll appear here in real-time."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Search />}
          title="No matches"
          description={`No crashes match "${search}". Try a different search term.`}
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border/50 bg-card/40 backdrop-blur">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/20 hover:bg-muted/20">
                <TableHead className="h-10 px-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Time
                </TableHead>
                <TableHead className="h-10 px-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Container
                </TableHead>
                <TableHead className="h-10 px-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Severity
                </TableHead>
                <TableHead className="h-10 px-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Category
                </TableHead>
                <TableHead className="h-10 px-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Exit
                </TableHead>
                <TableHead className="h-10 px-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Cache
                </TableHead>
                <TableHead className="h-10 px-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Status
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <AnimatePresence initial={false}>
                {filtered.map((crash) => {
                  const isFlashing = flashIds.has(crash.id);
                  const sevTint = severityToken(crash.severity);
                  let timeAgo = "";
                  try {
                    timeAgo = formatDistanceToNow(parseISO(crash.created_at), {
                      addSuffix: true,
                    });
                  } catch {
                    timeAgo = crash.created_at;
                  }
                  return (
                    <motion.tr
                      key={crash.id}
                      layoutId={`crash-${crash.id}`}
                      initial={
                        isFlashing
                          ? {
                              opacity: 0,
                              y: -12,
                              backgroundColor: `color-mix(in oklab, ${sevTint} 20%, transparent)`,
                            }
                          : { opacity: 0 }
                      }
                      animate={{
                        opacity: 1,
                        y: 0,
                        backgroundColor: isFlashing
                          ? "rgba(0,0,0,0)"
                          : undefined,
                      }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 1.2, ease: "easeOut" }}
                      onClick={() => router.push(`/crashes/${crash.id}`)}
                      className={cn(
                        "cursor-pointer border-b border-border/30 transition-colors hover:bg-muted/50",
                      )}
                    >
                      <td
                        className="px-4 py-3 align-middle font-mono text-xs tabular-nums text-muted-foreground"
                        title={crash.created_at}
                      >
                        {timeAgo}
                      </td>
                      <td className="px-4 py-3 align-middle">
                        <div className="flex flex-col">
                          <span className="font-mono text-sm font-semibold text-foreground">
                            {crash.container_name}
                          </span>
                          <span className="font-mono text-xs text-muted-foreground">
                            {crash.image}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 align-middle">
                        <SeverityBadge severity={crash.severity} />
                      </td>
                      <td className="px-4 py-3 align-middle">
                        {crash.category ? (
                          <span className="inline-flex items-center rounded-full border border-border/60 px-2 py-0.5 text-xs font-medium text-muted-foreground">
                            {crash.category}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-middle font-mono text-sm tabular-nums">
                        {crash.exit_code ?? (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-middle">
                        {crash.cache_hit ? (
                          <span
                            title="Cached analysis — no LLM call"
                            className="inline-flex items-center text-[var(--color-accent-cyan)]"
                          >
                            <Zap className="h-4 w-4" aria-hidden="true" />
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-middle">
                        <StatusPill crash={crash} />
                      </td>
                    </motion.tr>
                  );
                })}
              </AnimatePresence>
            </TableBody>
          </Table>
        </div>
      )}

      {/* Footer link helper */}
      <div className="sr-only">
        <Link href="/crashes">Crashes list</Link>
      </div>
    </motion.div>
  );
}
