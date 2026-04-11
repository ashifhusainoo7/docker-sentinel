"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { setTokens } from "@/lib/auth";

export default function CallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (accessToken && refreshToken) {
      setTokens(accessToken, refreshToken);
      router.push("/");
    } else {
      router.push("/login");
    }
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">Signing in...</p>
    </div>
  );
}
