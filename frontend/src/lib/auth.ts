const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getMe(): Promise<{ user: UserPayload; tenant_name: string; tenant_slug: string } | null> {
  const res = await fetch(`${API_URL}/api/v1/auth/me`, {
    credentials: "include",
  });
  if (!res.ok) return null;
  return res.json();
}

export async function logout(): Promise<void> {
  await fetch(`${API_URL}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export interface UserPayload {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  role: string;
}
