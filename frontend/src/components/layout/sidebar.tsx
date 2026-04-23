import Link from "next/link";
import { NavLinks } from "@/components/layout/nav-links";
import { AnimatedGradient } from "@/components/ui/motion/animated-gradient";

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 border-r border-border/40 bg-sidebar/80 backdrop-blur md:flex md:flex-col">
      <div className="flex h-16 items-center px-6">
        <Link href="/" className="text-lg font-bold tracking-tight">
          <AnimatedGradient>DockerSentinel</AnimatedGradient>
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto py-4">
        <NavLinks />
      </div>
      <div className="border-t border-border/40 p-4 text-xs text-muted-foreground">
        v0.1.0 · AI-powered crash intel
      </div>
    </aside>
  );
}
