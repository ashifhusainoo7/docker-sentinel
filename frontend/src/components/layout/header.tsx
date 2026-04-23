"use client";

import { useAuth } from "@/hooks/use-auth";
import { useWebsocketStatus } from "@/hooks/use-websocket";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Shimmer } from "@/components/ui/motion/shimmer";
import { LiveIndicator } from "@/components/ui/live-indicator";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { LogOut, User as UserIcon } from "lucide-react";

function HeaderSkeleton() {
  return (
    <header className="flex h-16 items-center justify-end gap-4 border-b border-border/40 bg-background/60 px-6 backdrop-blur">
      <Shimmer className="h-4 w-24 rounded" />
      <Shimmer className="h-8 w-8 rounded-full" />
    </header>
  );
}

export function Header() {
  const { user, tenantName, loading, logout } = useAuth();
  const wsStatus = useWebsocketStatus();

  if (loading) return <HeaderSkeleton />;

  const initials =
    user?.name
      ?.split(" ")
      .map((s) => s[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() ??
    user?.email?.[0]?.toUpperCase() ??
    "?";

  return (
    <header className="flex h-16 items-center justify-between gap-4 border-b border-border/40 bg-background/60 px-6 backdrop-blur">
      <div className="flex items-center gap-3">
        {tenantName && (
          <span className="text-sm text-muted-foreground">
            <span className="text-foreground font-medium">{tenantName}</span>
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <LiveIndicator state={wsStatus} />
        <ThemeToggle />

        {user && (
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-full"
                  aria-label="Account menu"
                >
                  <Avatar className="h-8 w-8">
                    {user.avatar_url && <AvatarImage src={user.avatar_url} alt="" />}
                    <AvatarFallback>{initials}</AvatarFallback>
                  </Avatar>
                </Button>
              }
            />
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium">{user.name ?? user.email}</span>
                  <span className="text-xs text-muted-foreground">{user.email}</span>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                render={<a href="/settings" className="cursor-pointer" />}
              >
                <UserIcon className="mr-2 h-4 w-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => logout()}
                className="cursor-pointer text-destructive focus:text-destructive"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </header>
  );
}
