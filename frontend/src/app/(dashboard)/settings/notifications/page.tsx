"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  AlertTriangle,
  Bell,
  Loader2,
  Mail,
  MessageSquare,
  Phone,
  RefreshCw,
  Send,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { GlowCard } from "@/components/ui/motion/glow-card";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonCard } from "@/components/ui/skeleton";
import {
  testNotificationChannel,
  updateNotificationConfig,
  useNotificationConfigs,
  type NotificationChannel,
  type NotificationConfig,
} from "@/hooks/use-notification-configs";
import { cn } from "@/lib/utils";

const CHANNEL_META: Record<
  NotificationChannel,
  {
    label: string;
    description: string;
    icon: typeof MessageSquare;
    tint: "cyan" | "violet" | "magenta";
  }
> = {
  slack: {
    label: "Slack",
    description: "Post crash alerts to a Slack channel via webhook.",
    icon: MessageSquare,
    tint: "cyan",
  },
  email: {
    label: "Email",
    description: "Send crash digests to one or more email addresses.",
    icon: Mail,
    tint: "violet",
  },
  voice: {
    label: "Voice",
    description: "Place an automated phone call for critical incidents.",
    icon: Phone,
    tint: "magenta",
  },
};

function describeConfig(config: NotificationConfig): string {
  const c = config.config ?? {};
  if (config.channel === "slack") {
    const url = typeof c.webhook_url === "string" ? c.webhook_url : "";
    if (!url) return "No webhook configured";
    return url.length > 40 ? `${url.slice(0, 40)}…` : url;
  }
  if (config.channel === "email") {
    const to = typeof c.to_email === "string" ? c.to_email : "";
    return to || "No recipient configured";
  }
  if (config.channel === "voice") {
    const phone = typeof c.phone_number === "string" ? c.phone_number : "";
    return phone || "No phone number configured";
  }
  return "";
}

// ---------------------------------------------------------------------------
// Inline toggle switch (reused checkbox pattern)
// ---------------------------------------------------------------------------

interface ToggleSwitchProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  id: string;
  label: string;
}

function ToggleSwitch({ checked, onChange, disabled, id, label }: ToggleSwitchProps) {
  return (
    <span className="relative inline-flex flex-shrink-0">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        aria-label={label}
        className="peer sr-only"
      />
      <span
        className={cn(
          "flex h-5 w-9 cursor-pointer items-center rounded-full border border-border/60 bg-muted px-0.5 transition-colors",
          "peer-checked:border-[oklch(0.72_0.15_205)] peer-checked:bg-[oklch(0.72_0.15_205/0.35)]",
          "peer-focus-visible:ring-2 peer-focus-visible:ring-ring/50",
          "peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
        )}
        onClick={() => !disabled && onChange(!checked)}
        role="presentation"
      >
        <span
          className={cn(
            "h-3.5 w-3.5 rounded-full bg-foreground/70 shadow-sm transition-transform",
            checked ? "translate-x-4" : "translate-x-0",
          )}
        />
      </span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Channel card
// ---------------------------------------------------------------------------

interface ChannelCardProps {
  config: NotificationConfig;
  index: number;
  onToggled: () => void;
}

function ChannelCard({ config, index, onToggled }: ChannelCardProps) {
  const meta = CHANNEL_META[config.channel];
  const Icon = meta.icon;
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [enabled, setEnabled] = useState(config.is_enabled);

  // Re-seed local state whenever the server-backed prop changes. Without this,
  // an optimistic rollback that disagrees with the next refresh (e.g. server
  // actually persisted the new value) leaves the UI stuck on stale state.
  useEffect(() => {
    setEnabled(config.is_enabled);
  }, [config.is_enabled]);

  const handleToggle = async (next: boolean) => {
    setSaving(true);
    const previous = enabled;
    setEnabled(next); // optimistic
    try {
      await updateNotificationConfig(config.channel, { is_enabled: next });
      toast.success(
        `${meta.label} notifications ${next ? "enabled" : "disabled"}`,
      );
      onToggled();
    } catch (e: unknown) {
      setEnabled(previous);
      const msg = e instanceof Error ? e.message : "Update failed";
      toast.error(`Could not update ${meta.label}`, { description: msg });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      await testNotificationChannel(config.channel);
      toast.success(`${meta.label} test sent`, {
        description: "Check the channel to confirm delivery.",
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Test failed";
      toast.error(`${meta.label} test failed`, { description: msg });
    } finally {
      setTesting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.06, ease: "easeOut" }}
    >
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
                <p className="text-xs text-muted-foreground">
                  {meta.description}
                </p>
              </div>
            </div>
            <ToggleSwitch
              id={`toggle-${config.channel}`}
              label={`Enable ${meta.label} notifications`}
              checked={enabled}
              onChange={handleToggle}
              disabled={saving}
            />
          </div>

          <div className="rounded-lg border border-border/40 bg-muted/20 px-3 py-2 font-mono text-xs text-muted-foreground break-all">
            {describeConfig(config)}
          </div>

          <div className="flex items-center justify-between gap-2 border-t border-border/40 pt-3">
            <span className="text-xs text-muted-foreground">
              {enabled ? (
                config.use_platform_default
                  ? "Using platform default"
                  : "Custom configuration"
              ) : (
                "Disabled"
              )}
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={handleTest}
              disabled={!enabled || testing}
            >
              {testing ? (
                <>
                  <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="mr-1.5 size-3.5" />
                  Send test
                </>
              )}
            </Button>
          </div>
        </div>
      </GlowCard>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function NotificationsSettingsPage() {
  const { configs, loading, error, refresh } = useNotificationConfigs();

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Notification Channels</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure how DockerSentinel alerts you when crashes happen.
        </p>
      </div>

      {loading && configs.length === 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : error ? (
        <EmptyState
          icon={<AlertTriangle />}
          title="Could not load notification settings"
          description={error.message}
          action={
            <Button onClick={() => refresh()}>
              <RefreshCw className="mr-1.5 size-4" />
              Retry
            </Button>
          }
        />
      ) : configs.length === 0 ? (
        <EmptyState
          icon={<Bell />}
          title="No notification channels configured"
          description="Your tenant admin hasn't set up notification channels yet. Ask them to configure Slack, email, or voice in this tenant."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {configs.map((config, i) => (
            <ChannelCard
              key={config.id}
              config={config}
              index={i}
              onToggled={refresh}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
