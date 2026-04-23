const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function refreshOnce(): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  return res.ok;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    _retry = false,
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
      credentials: "include",
    });

    if (response.status === 401 && !_retry && !path.startsWith("/api/v1/auth/")) {
      const refreshed = await refreshOnce();
      if (refreshed) {
        return this.request<T>(path, options, true);
      }
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  }

  get<T>(path: string) {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  put<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  delete(path: string) {
    return this.request(path, { method: "DELETE" });
  }
}

export const api = new ApiClient(API_URL);
