"use client";

import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

export function Header() {
  const { user, tenantName, logout } = useAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b px-6">
      <div>
        <span className="text-sm text-muted-foreground">{tenantName}</span>
      </div>
      <div className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-sm">{user.name || user.email}</span>
            <Button variant="outline" size="sm" onClick={logout}>
              Logout
            </Button>
          </>
        )}
      </div>
    </header>
  );
}
