"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { formatDistanceToNow, parseISO } from "date-fns";
import { toast } from "sonner";
import {
  AlertTriangle,
  MoreVertical,
  Plug,
  RefreshCw,
  Server,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { GlowCard } from "@/components/ui/motion/glow-card";
import { PulseDot, type PulseDotState } from "@/components/ui/motion/pulse-dot";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonCard } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  deleteHost,
  testHostConnection,
  useDockerHosts,
  type DockerHost,
} from "@/hooks/use-docker-hosts";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Deterministic sparkline — seeded by host id so each card is stable between
// renders, but different hosts get different curves.
// ---------------------------------------------------------------------------

function seededRandom(seed: number) {
  // Mulberry32 — fast, deterministic 32-bit PRNG.
  let t = seed >>> 0;
  return function next() {
    t = (t + 0x6d2b79f5) >>> 0;
    let r = t;
    r = Math.imul(r ^ (r >>> 15), r | 1);
    r ^= r + Math.imul(r ^ (r >>> 7), r | 61);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function sparklinePoints(seed: string, count = 12, max = 10): number[] {
  const rng = seededRandom(hashString(seed));
  const points: number[] = [];
  let prev = rng() * max;
  for (let i = 0; i < count; i++) {
    // Random-walk style: drift + noise, clamped to [0, max].
    const drift = (rng() - 0.5) * max * 0.6;
    prev = Math.max(0, Math.min(max, prev + drift));
    points.push(prev);
  }
  return points;
}

interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
  color?: string;
}

function Sparkline({
  values,
  width = 220,
  height = 40,
  color = "oklch(0.72 0.15 205)",
}: SparklineProps) {
  if (values.length < 2) return null;
  const max = Math.max(...values, 1);
  const stepX = width / (values.length - 1);
  const toY = (v: number) => height - (v / max) * (height - 4) - 2;

  const linePath = values
    .map((v, i) => `${i === 0 ? "M" : "L"} ${(i * stepX).toFixed(2)} ${toY(v).toFixed(2)}`)
    .join(" ");

  const areaPath = `${linePath} L ${width} ${height} L 0 ${height} Z`;

  // Unique gradient id per sparkline instance to avoid collisions.
  const gradId = `sparkline-grad-${hashString(values.join(",")).toString(36)}`;

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="block"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Status mapping — collapse backend status string to PulseDot state.
// ---------------------------------------------------------------------------

function hostStatus(host: DockerHost): PulseDotState {
  const s = (host.status ?? "").toLowerCase();
  if (s === "connected") return "live";
  if (s === "pending") return "connecting";
  return "offline";
}

function statusLabel(host: DockerHost): string {
  const s = (host.status ?? "unknown").toLowerCase();
  switch (s) {
    case "connected":
      return "Connected";
    case "pending":
      return "Connecting";
    case "disconnected":
      return "Disconnected";
    case "error":
      return "Error";
    default:
      return host.status || "Unknown";
  }
}

function connectionTimestamp(host: DockerHost): string {
  const raw = host.agent_last_seen ?? host.updated_at;
  try {
    return formatDistanceToNow(parseISO(raw), { addSuffix: true });
  } catch {
    return raw;
  }
}

// ---------------------------------------------------------------------------
// Host card
// ---------------------------------------------------------------------------

interface HostCardProps {
  host: DockerHost;
  index: number;
  onRequestDelete: (host: DockerHost) => void;
  onTest: (host: DockerHost) => void;
  testingId: string | null;
}

function HostCard({ host, index, onRequestDelete, onTest, testingId }: HostCardProps) {
  const state = hostStatus(host);
  const sparkValues = useMemo(() => sparklinePoints(host.id), [host.id]);
  const isTesting = testingId === host.id;

  const isTcp = host.connection_mode === "tcp";
  const modeChipClass = isTcp
    ? "bg-[oklch(0.62_0.20_290/0.15)] text-[oklch(0.78_0.16_290)] ring-1 ring-[oklch(0.62_0.20_290/0.35)]"
    : "bg-[oklch(0.72_0.15_205/0.15)] text-[oklch(0.82_0.14_205)] ring-1 ring-[oklch(0.72_0.15_205/0.35)]";

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05, ease: "easeOut" }}
    >
      <GlowCard tint={isTcp ? "violet" : "cyan"} className="h-full">
        <div className="flex flex-col gap-4 p-5">
          {/* Top row: dot + name + overflow */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2">
              <PulseDot state={state} />
              <h3 className="truncate font-mono text-base font-semibold tracking-tight">
                {host.name}
              </h3>
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Actions for ${host.name}`}
                  >
                    <MoreVertical />
                  </Button>
                }
              />
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem
                  onClick={() => onTest(host)}
                  className="cursor-pointer"
                  disabled={isTesting}
                >
                  <Plug className="mr-2 h-4 w-4" />
                  {isTesting ? "Testing..." : "Test Connection"}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  variant="destructive"
                  className="cursor-pointer"
                  onClick={() => onRequestDelete(host)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Connection mode pill + endpoint */}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em]",
                modeChipClass,
              )}
            >
              {isTcp ? "Direct TCP" : "Agent"}
            </span>
            <span className="text-xs text-muted-foreground">
              {statusLabel(host)}
            </span>
          </div>

          <div className="font-mono text-xs text-muted-foreground break-all">
            {isTcp
              ? (host.tcp_url ?? "No endpoint configured")
              : (host.agent_id ?? "Waiting for agent")}
          </div>

          {/* Sparkline */}
          <div className="-mx-1">
            <Sparkline
              values={sparkValues}
              color={
                state === "live"
                  ? "oklch(0.72 0.15 205)"
                  : state === "connecting"
                    ? "oklch(0.80 0.15 75)"
                    : "oklch(0.62 0.12 260)"
              }
            />
          </div>

          {/* Bottom meta */}
          <div className="flex items-center justify-between border-t border-border/40 pt-3 text-xs text-muted-foreground">
            <span>
              {state === "live" ? "Connected" : "Last seen"} {connectionTimestamp(host)}
            </span>
            {host.tls_enabled && isTcp && (
              <span className="inline-flex items-center rounded-full border border-border/60 px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
                TLS
              </span>
            )}
          </div>
        </div>
      </GlowCard>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function HostsPage() {
  const { hosts, loading, error, refresh } = useDockerHosts();
  const [pendingDelete, setPendingDelete] = useState<DockerHost | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);

  const handleTest = async (host: DockerHost) => {
    setTestingId(host.id);
    try {
      const result = await testHostConnection(host.id);
      if (result.ok) {
        const bits = [
          result.docker_version && `Docker ${result.docker_version}`,
          typeof result.running_containers === "number" &&
            `${result.running_containers} running containers`,
          result.latency_ms != null && `${result.latency_ms}ms`,
        ].filter(Boolean);
        toast.success("Connection OK", {
          description: bits.length ? bits.join(" · ") : `${host.name} responded.`,
        });
      } else {
        toast.error("Connection failed", {
          description: result.message ?? "Probe returned no detail.",
        });
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Test failed";
      toast.error("Connection failed", { description: msg });
    } finally {
      setTestingId(null);
    }
  };

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deleteHost(pendingDelete.id);
      toast.success("Host removed", {
        description: `${pendingDelete.name} was deleted.`,
      });
      setPendingDelete(null);
      refresh();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Delete failed";
      toast.error("Could not delete host", { description: msg });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Docker Hosts</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Every host streaming container telemetry to DockerSentinel.
          </p>
        </div>
        <Link href="/hosts/new">
          <Button>
            <Server className="mr-1.5 h-4 w-4" />
            Add Host
          </Button>
        </Link>
      </div>

      {/* Content */}
      {loading && hosts.length === 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : error ? (
        <EmptyState
          icon={<AlertTriangle />}
          title="Could not load hosts"
          description={error.message}
          action={
            <Button onClick={() => refresh()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          }
        />
      ) : hosts.length === 0 ? (
        <EmptyState
          icon={<Server />}
          title="No hosts connected"
          description="Add your first Docker host to start monitoring crashes."
          action={
            <Link href="/hosts/new">
              <Button>Add Host</Button>
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {hosts.map((host, i) => (
            <HostCard
              key={host.id}
              host={host}
              index={i}
              onRequestDelete={setPendingDelete}
              onTest={handleTest}
              testingId={testingId}
            />
          ))}
        </div>
      )}

      {/* Delete confirm dialog */}
      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open && !deleting) setPendingDelete(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this host?</DialogTitle>
            <DialogDescription>
              {pendingDelete
                ? `"${pendingDelete.name}" will stop reporting to DockerSentinel. Historical crashes remain in your account.`
                : ""}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" disabled={deleting} />}>
              Cancel
            </DialogClose>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete host"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
