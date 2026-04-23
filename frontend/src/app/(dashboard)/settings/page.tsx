"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Bell, ChevronRight, KeyRound, Siren, Users } from "lucide-react";

import { GlowCard } from "@/components/ui/motion/glow-card";
import type { ComponentType } from "react";

interface SettingsSection {
  href: string;
  title: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  tint: "cyan" | "violet" | "magenta";
}

const SECTIONS: SettingsSection[] = [
  {
    href: "/settings/api-keys",
    title: "API Keys",
    description: "Generate agent tokens and manage access.",
    icon: KeyRound,
    tint: "cyan",
  },
  {
    href: "/settings/members",
    title: "Team Members",
    description: "Invite teammates and manage roles.",
    icon: Users,
    tint: "violet",
  },
  {
    href: "/settings/notifications",
    title: "Notifications",
    description: "Slack, email, and voice channels.",
    icon: Bell,
    tint: "magenta",
  },
  {
    href: "/settings/escalations",
    title: "Escalations",
    description: "Auto-call rules when crashes spike.",
    icon: Siren,
    tint: "cyan",
  },
];

export default function SettingsPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Settings</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your tenant preferences and integrations
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {SECTIONS.map((section, i) => {
          const Icon = section.icon;
          return (
            <motion.div
              key={section.href}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: i * 0.06, ease: "easeOut" }}
              whileHover={{ y: -2 }}
            >
              <Link href={section.href} className="block">
                <GlowCard tint={section.tint} className="h-full">
                  <div className="flex items-start gap-4 p-5">
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted/50 ring-1 ring-border/50">
                      <Icon className="size-5 text-foreground" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="font-heading text-base font-semibold">
                        {section.title}
                      </h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {section.description}
                      </p>
                    </div>
                    <ChevronRight className="size-5 shrink-0 self-center text-muted-foreground transition-transform group-hover/glow:translate-x-0.5" />
                  </div>
                </GlowCard>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
