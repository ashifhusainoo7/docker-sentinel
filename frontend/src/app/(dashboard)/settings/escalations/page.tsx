"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  AlertTriangle,
  Mail,
  MessageSquare,
  Phone,
  Pencil,
  Plus,
  RefreshCw,
  Siren,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { GlowCard } from "@/components/ui/motion/glow-card";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonCard } from "@/components/ui/skeleton";
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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  createEscalationRule,
  deleteEscalationRule,
  updateEscalationRule,
  useEscalationRules,
  type EscalationAction,
  type EscalationRule,
  type EscalationRuleCreate,
} from "@/hooks/use-escalation-rules";
import { cn } from "@/lib/utils";

const ACTION_META: Record<
  EscalationAction,
  { label: string; icon: typeof MessageSquare; className: string }
> = {
  slack: {
    label: "Slack",
    icon: MessageSquare,
    className:
      "bg-[oklch(0.72_0.15_205/0.15)] text-[oklch(0.82_0.14_205)] ring-1 ring-[oklch(0.72_0.15_205/0.35)]",
  },
  email: {
    label: "Email",
    icon: Mail,
    className:
      "bg-[oklch(0.70_0.17_145/0.15)] text-[oklch(0.82_0.16_145)] ring-1 ring-[oklch(0.70_0.17_145/0.35)]",
  },
  call: {
    label: "Call",
    icon: Phone,
    className:
      "bg-[oklch(0.65_0.25_25/0.15)] text-[oklch(0.82_0.18_25)] ring-1 ring-[oklch(0.65_0.25_25/0.35)]",
  },
};

function describeCondition(condition: Record<string, unknown>): string {
  const type = typeof condition.type === "string" ? condition.type : "";
  if (type === "multi_crash") {
    const threshold =
      typeof condition.threshold === "number" ? condition.threshold : undefined;
    const window =
      typeof condition.window_minutes === "number"
        ? condition.window_minutes
        : undefined;
    if (threshold !== undefined && window !== undefined) {
      return `Triggers when ${threshold}+ crashes occur within ${window} minutes`;
    }
  }
  return "";
}

// ---------------------------------------------------------------------------
// Inline toggle switch (same pattern as notifications)
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
// Rule editor Sheet
// ---------------------------------------------------------------------------

interface RuleEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rule: EscalationRule | null;
  onSaved: () => void;
}

function RuleEditor({ open, onOpenChange, rule, onSaved }: RuleEditorProps) {
  const [name, setName] = useState("");
  const [threshold, setThreshold] = useState("3");
  const [windowMinutes, setWindowMinutes] = useState("10");
  const [action, setAction] = useState<EscalationAction>("slack");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (rule) {
      setName(rule.name);
      const cond = rule.condition ?? {};
      setThreshold(
        typeof cond.threshold === "number" ? String(cond.threshold) : "3",
      );
      setWindowMinutes(
        typeof cond.window_minutes === "number"
          ? String(cond.window_minutes)
          : "10",
      );
      setAction(rule.action);
      setIsActive(rule.is_active);
    } else {
      setName("");
      setThreshold("3");
      setWindowMinutes("10");
      setAction("slack");
      setIsActive(true);
    }
  }, [open, rule]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Name is required");
      return;
    }
    const t = parseInt(threshold, 10);
    const w = parseInt(windowMinutes, 10);
    if (!Number.isFinite(t) || t <= 0) {
      toast.error("Threshold must be a positive number");
      return;
    }
    if (!Number.isFinite(w) || w <= 0) {
      toast.error("Window must be a positive number of minutes");
      return;
    }

    setSaving(true);
    try {
      if (rule) {
        await updateEscalationRule(rule.id, {
          name: name.trim(),
          condition: { type: "multi_crash", threshold: t, window_minutes: w },
          action,
          is_active: isActive,
        });
        toast.success("Rule updated");
      } else {
        const payload: EscalationRuleCreate = {
          name: name.trim(),
          condition: { type: "multi_crash", threshold: t, window_minutes: w },
          action,
        };
        await createEscalationRule(payload);
        toast.success("Rule created");
      }
      onSaved();
      onOpenChange(false);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Save failed";
      toast.error("Could not save rule", { description: msg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        // Ignore close attempts (Esc / overlay-click) while a submit is in
        // flight. The Cancel button is already disabled during saving;
        // this covers the remaining dismiss paths so toasts don't fire
        // against a dismissed Sheet.
        if (!next && saving) return;
        onOpenChange(next);
      }}
    >
      <SheetContent className="w-full sm:max-w-md">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>{rule ? "Edit rule" : "New escalation rule"}</SheetTitle>
          <SheetDescription>
            Auto-trigger a notification when crash activity matches the condition.
          </SheetDescription>
        </SheetHeader>

        <form
          onSubmit={handleSubmit}
          className="flex flex-1 flex-col gap-5 overflow-y-auto px-6 pb-6"
        >
          <div className="space-y-1.5">
            <Label htmlFor="rule-name">Rule name</Label>
            <Input
              id="rule-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Crash storm"
              autoFocus
              disabled={saving}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label>Condition type</Label>
            <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2 text-sm">
              <span className="font-mono text-xs">multi_crash</span>
              <span className="ml-2 text-xs text-muted-foreground">
                (more condition types coming soon)
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="rule-threshold">Threshold</Label>
              <Input
                id="rule-threshold"
                type="number"
                min={1}
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                disabled={saving}
              />
              <p className="text-[11px] text-muted-foreground">
                Crashes required to fire
              </p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="rule-window">Window (min)</Label>
              <Input
                id="rule-window"
                type="number"
                min={1}
                value={windowMinutes}
                onChange={(e) => setWindowMinutes(e.target.value)}
                disabled={saving}
              />
              <p className="text-[11px] text-muted-foreground">
                Time window to count within
              </p>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Action</Label>
            <div className="grid grid-cols-3 gap-2">
              {(Object.keys(ACTION_META) as EscalationAction[]).map((a) => {
                const meta = ACTION_META[a];
                const Icon = meta.icon;
                const selected = action === a;
                return (
                  <button
                    key={a}
                    type="button"
                    onClick={() => setAction(a)}
                    disabled={saving}
                    className={cn(
                      "flex flex-col items-center justify-center gap-1 rounded-lg border px-3 py-3 text-xs font-medium transition-all",
                      selected
                        ? "border-ring bg-muted text-foreground ring-2 ring-ring/40"
                        : "border-border/60 bg-card/40 text-muted-foreground hover:border-border hover:text-foreground",
                    )}
                  >
                    <Icon className="size-4" />
                    {meta.label}
                  </button>
                );
              })}
            </div>
          </div>

          {rule && (
            <label
              htmlFor="rule-active"
              className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-border/60 bg-card/40 p-3"
            >
              <div>
                <div className="text-sm font-medium">Active</div>
                <div className="text-xs text-muted-foreground">
                  Disabled rules never fire.
                </div>
              </div>
              <ToggleSwitch
                id="rule-active"
                label="Active"
                checked={isActive}
                onChange={setIsActive}
                disabled={saving}
              />
            </label>
          )}

          <div className="mt-auto flex items-center justify-end gap-2 border-t border-border/50 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : rule ? "Save changes" : "Create rule"}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}

// ---------------------------------------------------------------------------
// Rule card
// ---------------------------------------------------------------------------

interface RuleCardProps {
  rule: EscalationRule;
  index: number;
  onEdit: (rule: EscalationRule) => void;
  onDelete: (rule: EscalationRule) => void;
  onToggled: () => void;
}

function RuleCard({ rule, index, onEdit, onDelete, onToggled }: RuleCardProps) {
  const meta = ACTION_META[rule.action];
  const Icon = meta.icon;
  const [saving, setSaving] = useState(false);
  const [active, setActive] = useState(rule.is_active);
  const summary = describeCondition(rule.condition);

  // Re-seed local state whenever the server-backed prop changes. Without this,
  // an optimistic rollback that disagrees with the next refresh leaves the UI
  // stuck on stale state.
  useEffect(() => {
    setActive(rule.is_active);
  }, [rule.is_active]);

  const handleToggle = async (next: boolean) => {
    const previous = active;
    setActive(next);
    setSaving(true);
    try {
      await updateEscalationRule(rule.id, { is_active: next });
      toast.success(next ? "Rule enabled" : "Rule disabled");
      onToggled();
    } catch (e: unknown) {
      setActive(previous);
      const msg = e instanceof Error ? e.message : "Update failed";
      toast.error("Could not update rule", { description: msg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05, ease: "easeOut" }}
    >
      <GlowCard tint={rule.action === "call" ? "magenta" : rule.action === "email" ? "violet" : "cyan"} className="h-full">
        <div className="flex flex-col gap-3 p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="truncate text-base font-semibold">{rule.name}</h3>
                {!active && (
                  <Badge variant="outline" className="text-[10px]">
                    Inactive
                  </Badge>
                )}
              </div>
            </div>
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em]",
                meta.className,
              )}
            >
              <Icon className="size-3" />
              {meta.label}
            </span>
          </div>

          {summary ? (
            <p className="text-sm text-muted-foreground">{summary}</p>
          ) : (
            <pre className="overflow-x-auto rounded-md border border-border/40 bg-muted/20 p-2 font-mono text-[11px] text-muted-foreground">
              {JSON.stringify(rule.condition, null, 2)}
            </pre>
          )}

          <div className="flex items-center justify-between gap-2 border-t border-border/40 pt-3">
            <div className="flex items-center gap-2">
              <ToggleSwitch
                id={`rule-${rule.id}-active`}
                label={`Enable ${rule.name}`}
                checked={active}
                onChange={handleToggle}
                disabled={saving}
              />
              <span className="text-xs text-muted-foreground">
                {active ? "Active" : "Inactive"}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={`Edit ${rule.name}`}
                onClick={() => onEdit(rule)}
              >
                <Pencil className="size-3.5" />
              </Button>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={`Delete ${rule.name}`}
                onClick={() => onDelete(rule)}
              >
                <Trash2 className="size-3.5 text-destructive" />
              </Button>
            </div>
          </div>
        </div>
      </GlowCard>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function EscalationsPage() {
  const { rules, loading, error, refresh } = useEscalationRules();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<EscalationRule | null>(null);
  const [pendingDelete, setPendingDelete] = useState<EscalationRule | null>(null);
  const [deleting, setDeleting] = useState(false);

  const openNew = () => {
    setEditingRule(null);
    setEditorOpen(true);
  };

  const openEdit = (rule: EscalationRule) => {
    setEditingRule(rule);
    setEditorOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deleteEscalationRule(pendingDelete.id);
      toast.success("Rule deleted");
      setPendingDelete(null);
      refresh();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Delete failed";
      toast.error("Could not delete rule", { description: msg });
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
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Escalation Rules</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Auto-trigger alerts when specific crash patterns occur.
          </p>
        </div>
        <Button onClick={openNew}>
          <Plus className="mr-1.5 size-4" />
          Add Rule
        </Button>
      </div>

      {loading && rules.length === 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : error ? (
        <EmptyState
          icon={<AlertTriangle />}
          title="Could not load rules"
          description={error.message}
          action={
            <Button onClick={() => refresh()}>
              <RefreshCw className="mr-1.5 size-4" />
              Retry
            </Button>
          }
        />
      ) : rules.length === 0 ? (
        <EmptyState
          icon={<Siren />}
          title="No escalation rules"
          description="Add a rule to trigger alerts when crashes spike."
          action={
            <Button onClick={openNew}>
              <Plus className="mr-1.5 size-4" />
              Add Rule
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {rules.map((rule, i) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              index={i}
              onEdit={openEdit}
              onDelete={setPendingDelete}
              onToggled={refresh}
            />
          ))}
        </div>
      )}

      <RuleEditor
        open={editorOpen}
        onOpenChange={setEditorOpen}
        rule={editingRule}
        onSaved={refresh}
      />

      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open && !deleting) setPendingDelete(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this rule?</DialogTitle>
            <DialogDescription>
              {pendingDelete
                ? `"${pendingDelete.name}" will stop firing immediately.`
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
              {deleting ? "Deleting..." : "Delete rule"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
