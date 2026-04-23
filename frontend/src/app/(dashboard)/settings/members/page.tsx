"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { formatDistanceToNow, parseISO } from "date-fns";
import { AlertTriangle, RefreshCw, UserPlus, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonTableRow } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
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
import { useMembers, type Member } from "@/hooks/use-members";

function initials(member: Member): string {
  const source = (member.name ?? member.email).trim();
  if (!source) return "?";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatJoined(value: string): string {
  try {
    return formatDistanceToNow(parseISO(value), { addSuffix: true });
  } catch {
    return value;
  }
}

function roleBadgeVariant(role: string): "default" | "secondary" | "outline" {
  const r = role.toLowerCase();
  if (r === "owner" || r === "admin") return "default";
  if (r === "member") return "secondary";
  return "outline";
}

interface GradientAvatarProps {
  member: Member;
}

function GradientAvatar({ member }: GradientAvatarProps) {
  return (
    <span
      className="flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white shadow-inner ring-1 ring-white/10"
      style={{
        background:
          "linear-gradient(135deg, oklch(0.72 0.15 205), oklch(0.62 0.20 290))",
      }}
      aria-hidden="true"
    >
      {initials(member)}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Invite dialog — backend returns 501, so we render coming-soon EmptyState
// ---------------------------------------------------------------------------

interface InviteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function InviteDialog({ open, onOpenChange }: InviteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Invite Member</DialogTitle>
          <DialogDescription>Add a teammate to this tenant.</DialogDescription>
        </DialogHeader>
        <EmptyState
          variant="coming-soon"
          title="Member invitations coming soon"
          description="We're still wiring up the invitation flow. In the meantime, share a direct link to dockersentinel.com and teammates can sign up through Google OAuth."
          action={
            <DialogClose render={<Button />}>Got it</DialogClose>
          }
        />
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function MembersPage() {
  const { members, loading, error, refresh } = useMembers();
  const [inviteOpen, setInviteOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Team Members</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Everyone with access to this tenant.
          </p>
        </div>
        <Button onClick={() => setInviteOpen(true)}>
          <UserPlus className="mr-1.5 size-4" />
          Invite Member
        </Button>
      </div>

      {loading && members.length === 0 ? (
        <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur">
          <SkeletonTableRow cols={4} />
          <SkeletonTableRow cols={4} />
          <SkeletonTableRow cols={4} />
          <SkeletonTableRow cols={4} />
        </div>
      ) : error ? (
        <EmptyState
          icon={<AlertTriangle />}
          title="Could not load members"
          description={error.message}
          action={
            <Button onClick={() => refresh()}>
              <RefreshCw className="mr-1.5 size-4" />
              Retry
            </Button>
          }
        />
      ) : members.length === 0 ? (
        <EmptyState
          icon={<Users />}
          title="No members yet"
          description="Your team members will appear here once they join."
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border/50 bg-card/60 backdrop-blur">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Member</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Joined</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.map((member, i) => (
                <motion.tr
                  key={member.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, delay: i * 0.04, ease: "easeOut" }}
                  className="border-b transition-colors hover:bg-muted/50"
                >
                  <TableCell className="p-2 align-middle whitespace-nowrap">
                    <div className="flex items-center gap-3">
                      <GradientAvatar member={member} />
                      <span className="font-medium">
                        {member.name ?? member.email}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="p-2 align-middle whitespace-nowrap font-mono text-xs text-muted-foreground">
                    {member.email}
                  </TableCell>
                  <TableCell className="p-2 align-middle whitespace-nowrap">
                    <Badge
                      variant={roleBadgeVariant(member.role)}
                      className="capitalize"
                    >
                      {member.role}
                    </Badge>
                  </TableCell>
                  <TableCell className="p-2 align-middle whitespace-nowrap text-xs text-muted-foreground">
                    Joined {formatJoined(member.created_at)}
                  </TableCell>
                </motion.tr>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} />
    </motion.div>
  );
}
