"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Home } from "lucide-react";

import { Button } from "@/components/ui/button";
import { MeshBackground } from "@/components/layout/mesh-background";
import { AnimatedGradient } from "@/components/ui/motion/animated-gradient";

/**
 * App-router 404 handler. Lives outside the (dashboard) route group so the
 * dashboard shell doesn't render — we ship our own MeshBackground to keep
 * the brand look consistent.
 */
export default function NotFound() {
  return (
    <div className="relative flex min-h-screen items-center justify-center p-6">
      <MeshBackground />
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
        className="relative w-full max-w-md rounded-2xl border border-border/50 bg-card/70 p-10 text-center shadow-[0_20px_60px_oklch(0.62_0.20_290/0.18)] backdrop-blur-xl"
      >
        <h1 className="font-heading text-7xl font-bold leading-none tracking-tight sm:text-8xl">
          <AnimatedGradient>404</AnimatedGradient>
        </h1>
        <p className="mt-4 text-base font-medium text-foreground">
          This page has crashed.
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          The route you&apos;re looking for doesn&apos;t exist (or did, and
          restarted somewhere else).
        </p>
        <div className="mt-6 flex justify-center">
          <Link href="/">
            <Button>
              <Home className="mr-1.5 h-4 w-4" />
              Back to dashboard
            </Button>
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
