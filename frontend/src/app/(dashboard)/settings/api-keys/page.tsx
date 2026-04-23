"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { formatDistanceToNow, parseISO } from "date-fns";
import { toast } from "sonner";
import {
  AlertTriangle,
  Check,
  Clipboard,
  KeyRound,
  RefreshCw,
  Trash2,
  TriangleAlert,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonTableRow } from "@/components/ui/skeleton";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  createApiKey,
  revokeApiKey,
  useApiKeys,
  type ApiKey,
  type ApiKeyCreated,
} from "@/hooks/use-api-keys";
import { cn } from "@/lib/utils";

const SCOPE_OPTIONS = ["agent", "read:crashes", "write:hosts"] as const;
const EXPIRES_PRESETS = [30, 90, 365] as const;

function formatDate(value: string | null): string {
  if (!value) return "Never";
  try {
    return new Date(value).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return value;
  }
}

function formatRelative(value: string | null): string {
  if (!value) return "Never";
  try {
    return formatDistanceToNow(parseISO(value), { addSuffix: true });
  } catch {
    return value;
  }
}

// ---------------------------------------------------------------------------
// Generate dialog
// ---------------------------------------------------------------------------

interface GenerateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}

function GenerateDialog({ open, onOpenChange, onCreated }: GenerateDialogProps) {
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<string[]>(["agent"]);
  const [expiresDays, setExpiresDays] = useState<number | null>(90);
  const [customDays, setCustomDays] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const resetForm = () => {
    setName("");
    setScopes(["agent"]);
    setExpiresDays(90);
    setCustomDays("");
    setCreated(null);
    setCopied(false);
    setSubmitting(false);
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      // If we have a created key and user closes, treat as "Done" → refresh.
      if (created) onCreated();
      resetForm();
    }
    onOpenChange(next);
  };

  const toggleScope = (scope: string) => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Name is required");
      return;
    }
    const days = customDays.trim() ? parseInt(customDays, 10) : expiresDays;
    setSubmitting(true);
    try {
      const res = await createApiKey({
        name: name.trim(),
        scopes,
        expires_in_days: days && !Number.isNaN(days) ? days : undefined,
      });
      setCreated(res);
      toast.success("API key generated");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to create API key";
      toast.error("Could not generate key", { description: msg });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopy = async () => {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.key);
      setCopied(true);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Copy failed — select and copy manually");
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        {!created ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <DialogHeader>
              <DialogTitle>Generate API key</DialogTitle>
              <DialogDescription>
                Create a token for an agent or integration. You will see the full key only once.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="api-key-name">Name</Label>
                <Input
                  id="api-key-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="production-agent"
                  autoFocus
                  required
                  disabled={submitting}
                />
              </div>

              <div className="space-y-1.5">
                <Label>Scopes</Label>
                <div className="flex flex-col gap-2">
                  {SCOPE_OPTIONS.map((scope) => (
                    <label
                      key={scope}
                      className="flex cursor-pointer items-center gap-2 rounded-md border border-border/60 bg-card/40 px-3 py-2 text-sm transition-colors hover:border-border"
                    >
                      <input
                        type="checkbox"
                        checked={scopes.includes(scope)}
                        onChange={() => toggleScope(scope)}
                        className="size-4 accent-[oklch(0.72_0.15_205)]"
                        disabled={submitting}
                      />
                      <span className="font-mono text-xs">{scope}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="api-key-expires">Expires in</Label>
                <div className="flex flex-wrap gap-2">
                  {EXPIRES_PRESETS.map((d) => (
                    <Button
                      key={d}
                      type="button"
                      size="sm"
                      variant={
                        expiresDays === d && !customDays ? "default" : "outline"
                      }
                      onClick={() => {
                        setExpiresDays(d);
                        setCustomDays("");
                      }}
                      disabled={submitting}
                    >
                      {d} days
                    </Button>
                  ))}
                  <Button
                    type="button"
                    size="sm"
                    variant={expiresDays === null && !customDays ? "default" : "outline"}
                    onClick={() => {
                      setExpiresDays(null);
                      setCustomDays("");
                    }}
                    disabled={submitting}
                  >
                    Never
                  </Button>
                </div>
                <Input
                  id="api-key-expires"
                  type="number"
                  min={1}
                  placeholder="Custom days"
                  value={customDays}
                  onChange={(e) => setCustomDays(e.target.value)}
                  disabled={submitting}
                  className="mt-2"
                />
              </div>
            </div>

            <DialogFooter>
              <DialogClose render={<Button variant="outline" type="button" disabled={submitting} />}>
                Cancel
              </DialogClose>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Generating..." : "Generate"}
              </Button>
            </DialogFooter>
          </form>
        ) : (
          <div className="space-y-4">
            <DialogHeader>
              <DialogTitle>Copy your API key</DialogTitle>
              <DialogDescription>
                This is the only time you will see this key. Copy it now and store it securely.
              </DialogDescription>
            </DialogHeader>

            <div className="flex items-start gap-2 rounded-lg border border-[oklch(0.80_0.15_75/0.4)] bg-[oklch(0.80_0.15_75/0.1)] p-3 text-xs">
              <TriangleAlert className="size-4 shrink-0 text-[oklch(0.80_0.15_75)]" />
              <span>
                For security, we do not store the full key. If you lose it, revoke this key and generate a new one.
              </span>
            </div>

            <motion.div
              animate={
                copied
                  ? { boxShadow: "0 0 0 0 oklch(0.72 0.15 205 / 0)" }
                  : {
                      boxShadow: [
                        "0 0 0 0 oklch(0.72 0.15 205 / 0.45)",
                        "0 0 0 10px oklch(0.72 0.15 205 / 0)",
                      ],
                    }
              }
              transition={
                copied
                  ? { duration: 0.3 }
                  : { duration: 1.6, repeat: Infinity, ease: "easeOut" }
              }
              className="rounded-lg border border-border/60 bg-card/80 p-3 backdrop-blur"
            >
              <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                {created.name}
              </div>
              <div className="break-all font-mono text-sm tracking-tight text-foreground select-all">
                {created.key}
              </div>
            </motion.div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                onClick={handleCopy}
                variant={copied ? "secondary" : "default"}
                className="flex-1"
              >
                {copied ? (
                  <>
                    <Check className="mr-1.5 size-4" />
                    Copied
                  </>
                ) : (
                  <>
                    <Clipboard className="mr-1.5 size-4" />
                    Copy key
                  </>
                )}
              </Button>
              <DialogClose
                render={
                  <Button
                    variant="outline"
                    onClick={() => {
                      onCreated();
                    }}
                  />
                }
              >
                Done
              </DialogClose>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ApiKeysPage() {
  const { keys, loading, error, refresh } = useApiKeys();
  const [generateOpen, setGenerateOpen] = useState(false);
  const [pendingRevoke, setPendingRevoke] = useState<ApiKey | null>(null);
  const [revoking, setRevoking] = useState(false);

  const handleRevoke = async () => {
    if (!pendingRevoke) return;
    setRevoking(true);
    try {
      await revokeApiKey(pendingRevoke.id);
      toast.success("API key revoked", {
        description: `${pendingRevoke.name} can no longer authenticate.`,
      });
      setPendingRevoke(null);
      refresh();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Revoke failed";
      toast.error("Could not revoke key", { description: msg });
    } finally {
      setRevoking(false);
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
          <h2 className="text-2xl font-bold tracking-tight">API Keys</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Tokens agents and integrations use to authenticate to DockerSentinel.
          </p>
        </div>
        <Button onClick={() => setGenerateOpen(true)}>
          <KeyRound className="mr-1.5 size-4" />
          Generate Key
        </Button>
      </div>

      {loading && keys.length === 0 ? (
        <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur">
          <SkeletonTableRow cols={4} />
          <SkeletonTableRow cols={4} />
          <SkeletonTableRow cols={4} />
        </div>
      ) : error ? (
        <EmptyState
          icon={<AlertTriangle />}
          title="Could not load API keys"
          description={error.message}
          action={
            <Button onClick={() => refresh()}>
              <RefreshCw className="mr-1.5 size-4" />
              Retry
            </Button>
          }
        />
      ) : keys.length === 0 ? (
        <EmptyState
          icon={<KeyRound />}
          title="No API keys yet"
          description="Generate your first key to start deploying agents."
          action={
            <Button onClick={() => setGenerateOpen(true)}>
              <KeyRound className="mr-1.5 size-4" />
              Generate Key
            </Button>
          }
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border/50 bg-card/60 backdrop-blur">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Prefix</TableHead>
                <TableHead>Scopes</TableHead>
                <TableHead>Last used</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead className="w-[1%]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((key) => (
                <TableRow key={key.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <span>{key.name}</span>
                      {!key.is_active && (
                        <Badge variant="destructive" className="text-[10px]">
                          Revoked
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                    {key.key_prefix}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {key.scopes.length === 0 ? (
                        <span className="text-xs text-muted-foreground">none</span>
                      ) : (
                        key.scopes.map((scope) => (
                          <Badge
                            key={scope}
                            variant="secondary"
                            className={cn("font-mono text-[10px]")}
                          >
                            {scope}
                          </Badge>
                        ))
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatRelative(key.last_used_at)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(key.expires_at)}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Revoke ${key.name}`}
                      onClick={() => setPendingRevoke(key)}
                      disabled={!key.is_active}
                    >
                      <Trash2 className="size-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <GenerateDialog
        open={generateOpen}
        onOpenChange={setGenerateOpen}
        onCreated={refresh}
      />

      <Dialog
        open={pendingRevoke !== null}
        onOpenChange={(open) => {
          if (!open && !revoking) setPendingRevoke(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke this API key?</DialogTitle>
            <DialogDescription>
              {pendingRevoke
                ? `"${pendingRevoke.name}" will stop working immediately. Any agent using this key will need a new one.`
                : ""}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" disabled={revoking} />}>
              Cancel
            </DialogClose>
            <Button variant="destructive" onClick={handleRevoke} disabled={revoking}>
              {revoking ? "Revoking..." : "Revoke key"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
