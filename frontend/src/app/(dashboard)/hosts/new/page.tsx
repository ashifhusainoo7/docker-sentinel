"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  Radio,
  Server,
  ShieldCheck,
  Terminal,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GlowCard } from "@/components/ui/motion/glow-card";
import { createHost } from "@/hooks/use-docker-hosts";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ConnectionMode = "tcp" | "agent";

interface FormState {
  mode: ConnectionMode | null;
  name: string;
  tcp_url: string;
  tls_enabled: boolean;
  monitor_all_containers: boolean;
}

const INITIAL_STATE: FormState = {
  mode: null,
  name: "",
  tcp_url: "",
  tls_enabled: false,
  monitor_all_containers: true,
};

const STEPS = [
  { id: 1, label: "Connection" },
  { id: 2, label: "Details" },
  { id: 3, label: "Review" },
] as const;

// ---------------------------------------------------------------------------
// Styled checkbox-as-switch — Shadcn base-nova doesn't ship a Switch, so we
// render a styled checkbox that behaves identically.
// ---------------------------------------------------------------------------

interface ToggleProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  id: string;
  label: string;
  description?: string;
}

function Toggle({ checked, onChange, id, label, description }: ToggleProps) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start justify-between gap-4 rounded-lg border border-border/60 bg-card/40 p-3 transition-colors hover:border-border"
    >
      <div className="flex flex-col gap-1">
        <span className="text-sm font-medium">{label}</span>
        {description && (
          <span className="text-xs text-muted-foreground">{description}</span>
        )}
      </div>
      <span className="relative flex-shrink-0">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="peer sr-only"
        />
        <span
          className={cn(
            "flex h-5 w-9 items-center rounded-full border border-border/60 bg-muted px-0.5 transition-colors",
            "peer-checked:border-[oklch(0.72_0.15_205)] peer-checked:bg-[oklch(0.72_0.15_205/0.35)]",
            "peer-focus-visible:ring-2 peer-focus-visible:ring-ring/50",
          )}
        >
          <span
            className={cn(
              "h-3.5 w-3.5 rounded-full bg-foreground/70 shadow-sm transition-transform",
              checked ? "translate-x-4" : "translate-x-0",
            )}
          />
        </span>
      </span>
    </label>
  );
}

// ---------------------------------------------------------------------------
// Step header with progress bar
// ---------------------------------------------------------------------------

function StepProgress({ step }: { step: number }) {
  const pct = (step / STEPS.length) * 100;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        {STEPS.map((s) => {
          const active = step === s.id;
          const done = step > s.id;
          return (
            <div key={s.id} className="flex min-w-0 flex-1 items-center gap-2">
              <span
                className={cn(
                  "flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition-all",
                  done &&
                    "border-[oklch(0.72_0.15_205)] bg-[oklch(0.72_0.15_205/0.2)] text-[oklch(0.82_0.14_205)]",
                  active &&
                    "border-[oklch(0.72_0.15_205)] text-[oklch(0.82_0.14_205)] shadow-[0_0_14px_oklch(0.72_0.15_205/0.55)]",
                  !active && !done && "border-border/60 text-muted-foreground",
                )}
                aria-current={active ? "step" : undefined}
              >
                {done ? <Check className="h-3 w-3" /> : s.id}
              </span>
              <span
                className={cn(
                  "truncate text-xs font-medium uppercase tracking-wider",
                  active ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
      <div className="relative h-1 overflow-hidden rounded-full bg-border/60">
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[oklch(0.72_0.15_205)] to-[oklch(0.62_0.20_290)]"
          initial={false}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 25 }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 1 — connection mode picker
// ---------------------------------------------------------------------------

interface ModeCardProps {
  mode: ConnectionMode;
  selected: boolean;
  onSelect: () => void;
}

function ModeCard({ mode, selected, onSelect }: ModeCardProps) {
  const isTcp = mode === "tcp";
  const Icon = isTcp ? Server : Radio;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        "rounded-xl",
      )}
      aria-pressed={selected}
    >
      <GlowCard
        tint={isTcp ? "violet" : "cyan"}
        className={cn(
          "h-full transition-all",
          selected
            ? isTcp
              ? "ring-2 ring-[oklch(0.62_0.20_290)] shadow-[0_0_30px_oklch(0.62_0.20_290/0.35)]"
              : "ring-2 ring-[oklch(0.72_0.15_205)] shadow-[0_0_30px_oklch(0.72_0.15_205/0.35)]"
            : "",
        )}
      >
        <div className="flex flex-col gap-3 p-5">
          <div
            className={cn(
              "inline-flex h-10 w-10 items-center justify-center rounded-lg",
              isTcp
                ? "bg-[oklch(0.62_0.20_290/0.15)] text-[oklch(0.78_0.16_290)]"
                : "bg-[oklch(0.72_0.15_205/0.15)] text-[oklch(0.82_0.14_205)]",
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-heading text-base font-semibold">
              {isTcp ? "Direct TCP" : "Agent"}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {isTcp
                ? "Connect directly to the Docker daemon over TCP. Good for hosts you control."
                : "Install the DockerSentinel agent on the host. Works behind NAT/firewalls."}
            </p>
          </div>
          {selected && (
            <span className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-[oklch(0.82_0.14_205)]">
              <Check className="h-3 w-3" />
              Selected
            </span>
          )}
        </div>
      </GlowCard>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Summary row
// ---------------------------------------------------------------------------

function SummaryRow({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/40 py-2 last:border-b-0">
      <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
        {k}
      </span>
      <span className="font-mono text-xs text-right break-all">{v}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AddHostPage() {
  const router = useRouter();
  const [step, setStep] = useState<number>(1);
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [submitting, setSubmitting] = useState(false);
  // Track direction so AnimatePresence knows which way to slide.
  const [slideDir, setSlideDir] = useState<1 | -1>(1);

  const canAdvance = useMemo(() => {
    if (step === 1) return form.mode !== null;
    if (step === 2) {
      if (!form.name.trim()) return false;
      if (form.mode === "tcp" && !form.tcp_url.trim()) return false;
      return true;
    }
    return true;
  }, [step, form]);

  const advance = () => {
    if (!canAdvance) return;
    setSlideDir(1);
    setStep((s) => Math.min(STEPS.length, s + 1));
  };

  const retreat = () => {
    setSlideDir(-1);
    setStep((s) => Math.max(1, s - 1));
  };

  const handleSubmit = async () => {
    if (!form.mode) return;
    setSubmitting(true);
    try {
      const payload = {
        name: form.name.trim(),
        connection_mode: form.mode,
        monitor_all_containers: form.monitor_all_containers,
        ...(form.mode === "tcp"
          ? {
              tcp_url: form.tcp_url.trim(),
              tls_enabled: form.tls_enabled,
            }
          : {}),
      };
      await createHost(payload);
      toast.success("Host created", {
        description: `${form.name} is ready to monitor.`,
      });
      router.push("/hosts");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to create host";
      toast.error("Could not create host", { description: msg });
      setSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mx-auto max-w-3xl space-y-6"
    >
      {/* Back link + title */}
      <div className="space-y-3">
        <Link
          href="/hosts"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Hosts
        </Link>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Add Docker Host</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Pick a connection mode, fill in the details, and DockerSentinel will
            start watching this host for crashes.
          </p>
        </div>
      </div>

      {/* Progress */}
      <StepProgress step={step} />

      {/* Step body */}
      <div className="relative min-h-[360px]">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={step}
            initial={{ opacity: 0, x: slideDir * 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: slideDir * -20 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="space-y-5"
          >
            {step === 1 && (
              <Step1
                selected={form.mode}
                onSelect={(mode) => setForm((f) => ({ ...f, mode }))}
              />
            )}
            {step === 2 && (
              <Step2 form={form} setForm={setForm} />
            )}
            {step === 3 && <Step3 form={form} />}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Footer nav */}
      <div className="flex items-center justify-between gap-3 border-t border-border/40 pt-5">
        {step > 1 ? (
          <Button variant="outline" onClick={retreat} disabled={submitting}>
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            Back
          </Button>
        ) : (
          <span />
        )}

        {step < STEPS.length ? (
          <Button onClick={advance} disabled={!canAdvance}>
            Next
            <ArrowRight className="ml-1.5 h-4 w-4" />
          </Button>
        ) : (
          <motion.div whileTap={{ scale: 0.97 }}>
            <Button
              onClick={handleSubmit}
              disabled={submitting}
              className="bg-gradient-to-r from-[oklch(0.72_0.15_205)] to-[oklch(0.62_0.20_290)] text-white shadow-[0_0_24px_oklch(0.62_0.20_290/0.35)] hover:opacity-90"
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <ShieldCheck className="mr-1.5 h-4 w-4" />
                  Create Host
                </>
              )}
            </Button>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Steps
// ---------------------------------------------------------------------------

function Step1({
  selected,
  onSelect,
}: {
  selected: ConnectionMode | null;
  onSelect: (mode: ConnectionMode) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-heading text-lg font-semibold">
          Choose connection mode
        </h3>
        <p className="text-sm text-muted-foreground">
          Pick how DockerSentinel reaches this host.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <ModeCard
          mode="tcp"
          selected={selected === "tcp"}
          onSelect={() => onSelect("tcp")}
        />
        <ModeCard
          mode="agent"
          selected={selected === "agent"}
          onSelect={() => onSelect("agent")}
        />
      </div>
    </div>
  );
}

function Step2({
  form,
  setForm,
}: {
  form: FormState;
  setForm: React.Dispatch<React.SetStateAction<FormState>>;
}) {
  return (
    <div className="space-y-5">
      <div>
        <h3 className="font-heading text-lg font-semibold">
          {form.mode === "tcp" ? "Direct TCP details" : "Agent host details"}
        </h3>
        <p className="text-sm text-muted-foreground">
          {form.mode === "tcp"
            ? "Where should we connect, and does it use TLS?"
            : "Name the host — we'll issue an agent token after it's created."}
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="host-name">Name</Label>
        <Input
          id="host-name"
          placeholder="prod-api-01"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          autoFocus
        />
      </div>

      {form.mode === "tcp" && (
        <>
          <div className="space-y-2">
            <Label htmlFor="tcp-url">TCP URL</Label>
            <Input
              id="tcp-url"
              placeholder="tcp://192.168.1.100:2376"
              value={form.tcp_url}
              onChange={(e) =>
                setForm((f) => ({ ...f, tcp_url: e.target.value }))
              }
              className="font-mono"
            />
          </div>
          <Toggle
            id="tls-enabled"
            checked={form.tls_enabled}
            onChange={(v) => setForm((f) => ({ ...f, tls_enabled: v }))}
            label="TLS enabled"
            description="Verify the Docker daemon's certificate for this connection."
          />
        </>
      )}

      {form.mode === "agent" && (
        <div className="flex items-start gap-3 rounded-xl border border-border/60 bg-card/40 p-4 backdrop-blur">
          <span className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-[oklch(0.72_0.15_205/0.15)] text-[oklch(0.82_0.14_205)]">
            <Terminal className="h-4 w-4" />
          </span>
          <div className="space-y-1">
            <p className="text-sm font-medium">What happens next</p>
            <p className="text-xs text-muted-foreground">
              After creating this host, you&apos;ll get an install command and
              agent token to run on your target machine. The agent registers
              itself back to DockerSentinel over WebSocket.
            </p>
          </div>
        </div>
      )}

      <Toggle
        id="monitor-all"
        checked={form.monitor_all_containers}
        onChange={(v) =>
          setForm((f) => ({ ...f, monitor_all_containers: v }))
        }
        label="Monitor all containers"
        description="Capture crash events from every container on this host."
      />
    </div>
  );
}

function Step3({ form }: { form: FormState }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-heading text-lg font-semibold">Review and create</h3>
        <p className="text-sm text-muted-foreground">
          Confirm the details below. You can edit any setting after creation.
        </p>
      </div>

      <div className="rounded-xl border border-border/60 bg-card/40 p-4 backdrop-blur">
        <SummaryRow
          k="Connection mode"
          v={form.mode === "tcp" ? "Direct TCP" : "Agent"}
        />
        <SummaryRow k="Name" v={form.name || "—"} />
        {form.mode === "tcp" && (
          <>
            <SummaryRow k="TCP URL" v={form.tcp_url || "—"} />
            <SummaryRow
              k="TLS"
              v={form.tls_enabled ? "Enabled" : "Disabled"}
            />
          </>
        )}
        <SummaryRow
          k="Monitor all containers"
          v={form.monitor_all_containers ? "Yes" : "No"}
        />
      </div>
    </div>
  );
}
