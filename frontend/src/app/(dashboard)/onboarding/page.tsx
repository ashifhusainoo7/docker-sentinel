"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import {
  ArrowLeft,
  ArrowRight,
  Bell,
  Check,
  Clipboard,
  LayoutDashboard,
  Loader2,
  Mail,
  MessageSquare,
  Phone,
  Radio,
  Rocket,
  Server,
  Siren,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AnimatedGradient } from "@/components/ui/motion/animated-gradient";
import { GlowCard } from "@/components/ui/motion/glow-card";
import { createHost } from "@/hooks/use-docker-hosts";
import {
  updateNotificationConfig,
  type NotificationChannel,
} from "@/hooks/use-notification-configs";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types + step metadata
// ---------------------------------------------------------------------------

type ConnectionMode = "tcp" | "agent";

interface StepDescriptor {
  id: number;
  label: string;
}

const STEPS: StepDescriptor[] = [
  { id: 1, label: "Add Host" },
  { id: 2, label: "Configure Alerts" },
  { id: 3, label: "You're Ready" },
];

// ---------------------------------------------------------------------------
// Progress header — 3 dots + spring-animated fill, matches /hosts/new.
// ---------------------------------------------------------------------------

function StepProgress({
  steps,
  current,
}: {
  steps: StepDescriptor[];
  current: number;
}) {
  const pct = (current / steps.length) * 100;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        {steps.map((s) => {
          const active = current === s.id;
          const done = current > s.id;
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
// Page
// ---------------------------------------------------------------------------

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<number>(1);
  // 1 = advancing forward, -1 = moving back.
  const [slideDir, setSlideDir] = useState<1 | -1>(1);
  const [, setHostId] = useState<string | null>(null);

  const advance = () => {
    setSlideDir(1);
    setStep((s) => Math.min(STEPS.length, s + 1));
  };

  const retreat = () => {
    setSlideDir(-1);
    setStep((s) => Math.max(1, s - 1));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mx-auto max-w-3xl space-y-6 py-8"
    >
      {/* Hero */}
      <div className="space-y-2 text-center">
        <h1 className="font-heading text-3xl font-bold tracking-tight sm:text-4xl">
          <AnimatedGradient>Welcome to DockerSentinel</AnimatedGradient>
        </h1>
        <p className="text-sm text-muted-foreground sm:text-base">
          Three quick steps and you&apos;re monitoring containers in production.
        </p>
      </div>

      {/* Progress */}
      <StepProgress steps={STEPS} current={step} />

      {/* Step body */}
      <div className="relative min-h-[360px]">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={step}
            initial={{ opacity: 0, x: slideDir * 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: slideDir * -24 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="space-y-5"
          >
            {step === 1 && (
              <AddHostStep
                onCreated={(id) => {
                  setHostId(id);
                  advance();
                }}
              />
            )}
            {step === 2 && (
              <ConfigureAlertsStep onDone={advance} onSkip={advance} />
            )}
            {step === 3 && <ReadyStep onGoDashboard={() => router.push("/")} />}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Footer nav — only Back, only on step >= 2 */}
      {step >= 2 && (
        <div className="flex items-center justify-between gap-3 border-t border-border/40 pt-5">
          <Button variant="outline" onClick={retreat}>
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            Back
          </Button>
          <span />
        </div>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Step 1 — Add Host (compact inline wizard)
// ---------------------------------------------------------------------------

interface ModeOptionProps {
  mode: ConnectionMode;
  selected: boolean;
  onSelect: () => void;
}

function ModeOption({ mode, selected, onSelect }: ModeOptionProps) {
  const isTcp = mode === "tcp";
  const Icon = isTcp ? Server : Radio;
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className="group rounded-xl text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
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
                ? "Connect directly to the Docker daemon over TCP."
                : "Install a lightweight agent — works behind NAT."}
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

interface AddHostStepProps {
  onCreated: (hostId: string) => void;
}

function AddHostStep({ onCreated }: AddHostStepProps) {
  const [mode, setMode] = useState<ConnectionMode | null>(null);
  const [name, setName] = useState("");
  const [tcpUrl, setTcpUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = useMemo(() => {
    if (!mode) return false;
    if (!name.trim()) return false;
    if (mode === "tcp" && !tcpUrl.trim()) return false;
    return true;
  }, [mode, name, tcpUrl]);

  const handleSubmit = async () => {
    if (!mode || !canSubmit) return;
    setSubmitting(true);
    try {
      const host = await createHost({
        name: name.trim(),
        connection_mode: mode,
        monitor_all_containers: true,
        ...(mode === "tcp" ? { tcp_url: tcpUrl.trim(), tls_enabled: false } : {}),
      });
      toast.success("Host created", {
        description: `${host.name} is ready to monitor.`,
      });
      onCreated(host.id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to create host";
      toast.error("Could not create host", { description: msg });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-heading text-lg font-semibold">
          Add your first Docker host
        </h2>
        <p className="text-sm text-muted-foreground">
          Tell DockerSentinel where your containers live.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <ModeOption
          mode="tcp"
          selected={mode === "tcp"}
          onSelect={() => setMode("tcp")}
        />
        <ModeOption
          mode="agent"
          selected={mode === "agent"}
          onSelect={() => setMode("agent")}
        />
      </div>

      {mode && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="space-y-4 rounded-xl border border-border/60 bg-card/40 p-5 backdrop-blur"
        >
          <div className="space-y-2">
            <Label htmlFor="onboarding-host-name">Host name</Label>
            <Input
              id="onboarding-host-name"
              placeholder="prod-api-01"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          {mode === "tcp" && (
            <div className="space-y-2">
              <Label htmlFor="onboarding-tcp-url">TCP URL</Label>
              <Input
                id="onboarding-tcp-url"
                placeholder="tcp://192.168.1.100:2376"
                value={tcpUrl}
                onChange={(e) => setTcpUrl(e.target.value)}
                className="font-mono"
              />
            </div>
          )}
        </motion.div>
      )}

      <div className="flex justify-end">
        <motion.div whileTap={{ scale: 0.97 }}>
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
            className="bg-gradient-to-r from-[oklch(0.72_0.15_205)] to-[oklch(0.62_0.20_290)] text-white shadow-[0_0_24px_oklch(0.62_0.20_290/0.35)] hover:opacity-90"
          >
            {submitting ? (
              <>
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                Create host
                <ArrowRight className="ml-1.5 h-4 w-4" />
              </>
            )}
          </Button>
        </motion.div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 2 — Configure Alerts
// ---------------------------------------------------------------------------

interface ChannelMeta {
  channel: NotificationChannel;
  label: string;
  description: string;
  icon: typeof MessageSquare;
  tint: "cyan" | "violet" | "magenta";
  placeholder: string;
  fieldKey: "webhook_url" | "to_email" | "phone_number";
  fieldLabel: string;
  inputType: "text" | "email" | "tel";
}

const CHANNELS: ChannelMeta[] = [
  {
    channel: "slack",
    label: "Slack",
    description: "Post crash alerts to a Slack channel.",
    icon: MessageSquare,
    tint: "cyan",
    placeholder: "https://hooks.slack.com/services/...",
    fieldKey: "webhook_url",
    fieldLabel: "Webhook URL",
    inputType: "text",
  },
  {
    channel: "email",
    label: "Email",
    description: "Email digests of every crash event.",
    icon: Mail,
    tint: "violet",
    placeholder: "ops@example.com",
    fieldKey: "to_email",
    fieldLabel: "Recipient email",
    inputType: "email",
  },
  {
    channel: "voice",
    label: "Voice",
    description: "Automated call for critical incidents.",
    icon: Phone,
    tint: "magenta",
    placeholder: "+1 555 010 1234",
    fieldKey: "phone_number",
    fieldLabel: "Phone number",
    inputType: "tel",
  },
];

interface ChannelState {
  enabled: boolean;
  value: string;
}

interface ChannelCardProps {
  meta: ChannelMeta;
  state: ChannelState;
  onChange: (next: ChannelState) => void;
}

function ChannelCard({ meta, state, onChange }: ChannelCardProps) {
  const Icon = meta.icon;
  const inputId = `onboarding-${meta.channel}-value`;
  return (
    <GlowCard tint={meta.tint} className="h-full">
      <div className="flex flex-col gap-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted/50 ring-1 ring-border/50">
              <Icon className="size-5" />
            </div>
            <div className="min-w-0">
              <h3 className="font-heading text-base font-semibold">
                {meta.label}
              </h3>
              <p className="text-xs text-muted-foreground">{meta.description}</p>
            </div>
          </div>
          <label
            htmlFor={`onboarding-toggle-${meta.channel}`}
            className="relative inline-flex flex-shrink-0 cursor-pointer"
          >
            <input
              id={`onboarding-toggle-${meta.channel}`}
              type="checkbox"
              checked={state.enabled}
              onChange={(e) =>
                onChange({ ...state, enabled: e.target.checked })
              }
              aria-label={`Enable ${meta.label} notifications`}
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
                  state.enabled ? "translate-x-4" : "translate-x-0",
                )}
              />
            </span>
          </label>
        </div>
        <div className="space-y-2">
          <Label
            htmlFor={inputId}
            className={cn(!state.enabled && "text-muted-foreground")}
          >
            {meta.fieldLabel}
          </Label>
          <Input
            id={inputId}
            type={meta.inputType}
            value={state.value}
            disabled={!state.enabled}
            placeholder={meta.placeholder}
            onChange={(e) => onChange({ ...state, value: e.target.value })}
            className={cn(meta.channel === "slack" && "font-mono text-xs")}
          />
        </div>
      </div>
    </GlowCard>
  );
}

interface ConfigureAlertsStepProps {
  onDone: () => void;
  onSkip: () => void;
}

function ConfigureAlertsStep({ onDone, onSkip }: ConfigureAlertsStepProps) {
  const [states, setStates] = useState<Record<NotificationChannel, ChannelState>>({
    slack: { enabled: false, value: "" },
    email: { enabled: false, value: "" },
    voice: { enabled: false, value: "" },
  });
  const [saving, setSaving] = useState(false);

  const handleSaveAndContinue = async () => {
    const toSave = CHANNELS.filter((meta) => {
      const s = states[meta.channel];
      return s.enabled && s.value.trim().length > 0;
    });

    if (toSave.length === 0) {
      toast.info("No channels enabled", {
        description: "Use Skip for now to move on without configuring alerts.",
      });
      return;
    }

    setSaving(true);
    try {
      await Promise.all(
        toSave.map((meta) =>
          updateNotificationConfig(meta.channel, {
            is_enabled: true,
            config: { [meta.fieldKey]: states[meta.channel].value.trim() },
          }),
        ),
      );
      toast.success(
        toSave.length === 1
          ? `${CHANNELS.find((c) => c.channel === toSave[0].channel)?.label} channel saved`
          : `${toSave.length} channels saved`,
      );
      onDone();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Save failed";
      toast.error("Could not save notification channels", { description: msg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-[oklch(0.72_0.15_205/0.15)] text-[oklch(0.82_0.14_205)]">
          <Bell className="size-5" />
        </div>
        <div>
          <h2 className="font-heading text-lg font-semibold">
            Where should crashes land?
          </h2>
          <p className="text-sm text-muted-foreground">
            Turn on any channel you&apos;d like — you can change these any time
            in settings.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {CHANNELS.map((meta) => (
          <ChannelCard
            key={meta.channel}
            meta={meta}
            state={states[meta.channel]}
            onChange={(next) =>
              setStates((prev) => ({ ...prev, [meta.channel]: next }))
            }
          />
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button variant="ghost" onClick={onSkip} disabled={saving}>
          Skip for now
        </Button>
        <motion.div whileTap={{ scale: 0.97 }}>
          <Button
            onClick={handleSaveAndContinue}
            disabled={saving}
            className="bg-gradient-to-r from-[oklch(0.72_0.15_205)] to-[oklch(0.62_0.20_290)] text-white shadow-[0_0_24px_oklch(0.62_0.20_290/0.35)] hover:opacity-90"
          >
            {saving ? (
              <>
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                Save &amp; continue
                <ArrowRight className="ml-1.5 h-4 w-4" />
              </>
            )}
          </Button>
        </motion.div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 3 — You're Ready
// ---------------------------------------------------------------------------

const TEST_CRASH_CMD = "docker run --rm busybox sh -c 'exit 1'";

interface ReadyStepProps {
  onGoDashboard: () => void;
}

function ReadyStep({ onGoDashboard }: ReadyStepProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      if (typeof navigator === "undefined" || !navigator.clipboard) {
        throw new Error("Clipboard API unavailable");
      }
      await navigator.clipboard.writeText(TEST_CRASH_CMD);
      setCopied(true);
      toast.success("Command copied", {
        description: "Paste it into any terminal on a monitored host.",
      });
      window.setTimeout(() => setCopied(false), 1800);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Copy failed";
      toast.error("Could not copy command", { description: msg });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 240, damping: 18 }}
          className="flex size-16 items-center justify-center rounded-full bg-emerald-400/15 text-emerald-400 shadow-[0_0_30px_oklch(0.76_0.18_155/0.45)] ring-1 ring-emerald-400/40"
        >
          <Check className="size-8" strokeWidth={2.5} />
        </motion.div>
        <h2 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl">
          <AnimatedGradient>You&apos;re all set</AnimatedGradient>
        </h2>
        <p className="max-w-md text-sm text-muted-foreground">
          DockerSentinel is now watching your fleet. When containers crash,
          you&apos;ll see them on the dashboard and wherever you configured
          notifications.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <button
          type="button"
          onClick={onGoDashboard}
          className="group rounded-xl text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        >
          <GlowCard tint="cyan" className="h-full">
            <div className="flex flex-col gap-3 p-5">
              <div className="flex size-10 items-center justify-center rounded-lg bg-[oklch(0.72_0.15_205/0.15)] text-[oklch(0.82_0.14_205)]">
                <LayoutDashboard className="size-5" />
              </div>
              <div>
                <h3 className="font-heading text-base font-semibold">
                  Go to Dashboard
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Watch live crashes, metrics, and AI summaries roll in.
                </p>
              </div>
              <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-[oklch(0.82_0.14_205)]">
                Open dashboard
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </span>
            </div>
          </GlowCard>
        </button>

        <button
          type="button"
          onClick={handleCopy}
          className="group rounded-xl text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        >
          <GlowCard tint="magenta" className="h-full">
            <div className="flex flex-col gap-3 p-5">
              <div className="flex size-10 items-center justify-center rounded-lg bg-[oklch(0.65_0.25_340/0.15)] text-[oklch(0.78_0.18_340)]">
                <Siren className="size-5" />
              </div>
              <div>
                <h3 className="font-heading text-base font-semibold">
                  Trigger a test crash
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Copy this command and run it on any monitored host to see an
                  end-to-end alert.
                </p>
              </div>
              <div className="rounded-lg border border-border/40 bg-muted/30 px-3 py-2 font-mono text-xs break-all">
                {TEST_CRASH_CMD}
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-[oklch(0.78_0.18_340)]">
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    Copied
                  </>
                ) : (
                  <>
                    <Clipboard className="h-3.5 w-3.5" />
                    Copy command
                  </>
                )}
              </span>
            </div>
          </GlowCard>
        </button>
      </div>

      <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
        <Rocket className="h-3.5 w-3.5" />
        Need to tune things? Head to{" "}
        <span className="font-medium text-foreground">Settings</span> from the
        sidebar any time.
      </div>
    </div>
  );
}
