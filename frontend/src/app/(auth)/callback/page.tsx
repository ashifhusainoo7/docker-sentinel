"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { MeshBackground } from "@/components/layout/mesh-background";

function OrbitalSpinner() {
  return (
    <div className="relative h-20 w-20">
      {/* Outer ring */}
      <motion.div
        className="absolute inset-0 rounded-full border-2 border-transparent"
        style={{
          borderTopColor: "oklch(0.72 0.15 205)",
          borderRightColor: "oklch(0.72 0.15 205 / 0.3)",
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
      />
      {/* Middle ring */}
      <motion.div
        className="absolute inset-2 rounded-full border-2 border-transparent"
        style={{
          borderTopColor: "oklch(0.62 0.20 290)",
          borderLeftColor: "oklch(0.62 0.20 290 / 0.3)",
        }}
        animate={{ rotate: -360 }}
        transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }}
      />
      {/* Inner ring */}
      <motion.div
        className="absolute inset-5 rounded-full border-2 border-transparent"
        style={{
          borderTopColor: "oklch(0.65 0.25 340)",
          borderBottomColor: "oklch(0.65 0.25 340 / 0.3)",
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }}
      />
    </div>
  );
}

export default function CallbackPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/");
  }, [router]);

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center gap-6 overflow-hidden">
      <MeshBackground />
      <OrbitalSpinner />
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.4 }}
        className="text-sm uppercase tracking-[0.2em] text-muted-foreground"
      >
        Signing you in…
      </motion.p>
    </div>
  );
}
