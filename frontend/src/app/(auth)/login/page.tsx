"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { MeshBackground } from "@/components/layout/mesh-background";
import { AnimatedGradient } from "@/components/ui/motion/animated-gradient";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function GoogleLogo() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.08H42V20H24v8h11.3c-1.65 4.66-6.08 8-11.3 8-6.63 0-12-5.37-12-12s5.37-12 12-12c3.06 0 5.85 1.15 7.96 3.04l5.66-5.66C34.05 6.05 29.27 4 24 4 12.95 4 4 12.95 4 24s8.95 20 20 20 20-8.95 20-20c0-1.34-.14-2.65-.4-3.92z" />
      <path fill="#FF3D00" d="M6.31 14.69l6.57 4.82C14.66 15.05 18.96 12 24 12c3.06 0 5.85 1.15 7.96 3.04l5.66-5.66C34.05 6.05 29.27 4 24 4 16.32 4 9.66 8.34 6.31 14.69z" />
      <path fill="#4CAF50" d="M24 44c5.17 0 9.86-1.98 13.41-5.2l-6.19-5.24C29.14 34.82 26.72 36 24 36c-5.2 0-9.62-3.32-11.28-7.95l-6.53 5.03C9.49 39.56 16.23 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.08H42V20H24v8h11.3c-.79 2.24-2.24 4.17-4.08 5.57l.01-.01 6.19 5.24C37.0 38.53 44 33 44 24c0-1.34-.14-2.65-.4-3.92z" />
    </svg>
  );
}

export default function LoginPage() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden">
      <MeshBackground />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md px-6"
      >
        <div
          className="rounded-2xl border border-border/40 bg-card/60 p-8 shadow-2xl backdrop-blur-xl"
          style={{ backgroundColor: "var(--glass-bg)", borderColor: "var(--glass-border)" }}
        >
          <div className="mb-8 text-center">
            <AnimatedGradient className="text-3xl font-bold tracking-tight">
              DockerSentinel
            </AnimatedGradient>
            <p className="mt-2 text-sm text-muted-foreground">
              AI-Powered Container Crash Intelligence
            </p>
          </div>

          <motion.a
            href={`${API_URL}/api/v1/auth/google`}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="block rounded-lg"
            style={{ transition: "box-shadow 0.2s" }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-glow-violet)")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLElement).style.boxShadow = "none")
            }
          >
            <Button
              variant="outline"
              className="w-full gap-3 rounded-lg border-border/60 bg-background/40 py-6 text-base font-medium backdrop-blur"
            >
              <GoogleLogo />
              Continue with Google
            </Button>
          </motion.a>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            Protected by OAuth 2.0 · Your Google credentials never reach our servers
          </p>
        </div>
      </motion.div>
    </div>
  );
}
