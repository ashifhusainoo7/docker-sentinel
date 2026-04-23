"use client";

import { motion } from "framer-motion";

/**
 * Fixed-position decorative background for the dashboard shell.
 * Two radial gradient "blobs" drift slowly; 1px grid + noise on top.
 */
export function MeshBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      {/* Cyan blob */}
      <motion.div
        className="absolute h-[50vh] w-[50vw] rounded-full"
        style={{
          top: "-10%",
          right: "-10%",
          background: "radial-gradient(circle, oklch(0.72 0.15 205 / 0.18), transparent 70%)",
          filter: "blur(40px)",
        }}
        animate={{ x: [0, -30, 0], y: [0, 20, 0] }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* Violet blob */}
      <motion.div
        className="absolute h-[50vh] w-[50vw] rounded-full"
        style={{
          bottom: "-10%",
          left: "-10%",
          background: "radial-gradient(circle, oklch(0.62 0.20 290 / 0.16), transparent 70%)",
          filter: "blur(40px)",
        }}
        animate={{ x: [0, 30, 0], y: [0, -20, 0] }}
        transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* 1px grid overlay */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(to right, oklch(1 0 0) 1px, transparent 1px), linear-gradient(to bottom, oklch(1 0 0) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />
    </div>
  );
}
