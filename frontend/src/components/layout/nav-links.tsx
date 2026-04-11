"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Dashboard", icon: "LayoutDashboard" },
  { href: "/crashes", label: "Crashes", icon: "AlertTriangle" },
  { href: "/hosts", label: "Docker Hosts", icon: "Server" },
  { href: "/settings", label: "Settings", icon: "Settings" },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={cn(
            "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
            pathname === link.href
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          )}
        >
          <span>{link.label}</span>
        </Link>
      ))}
    </nav>
  );
}
