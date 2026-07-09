/**
 * API client for the RAG Knowledge Base backend.
 *
 * Provides type-safe HTTP methods with automatic token refresh
 * and error handling.
 *
 * Usage:
 *   import { api } from '@/lib/api';
 *   const { data } = await api.get<UserProfile>('/api/v1/auth/me');
 */

import type { ApiResponse, TokenResponse } from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Custom error for API failures. */
export class ApiError extends Error {
  constructor(
    public code: number,
    message: string,
    public data?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Token storage keys. */
const TOKEN_KEY = "rag_access_token";
const REFRESH_TOKEN_KEY = "rag_refresh_token";

/** Token management utilities. */
export const tokenStorage = {
  getAccessToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  },

  getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setTokens(tokens: TokenResponse): void {
    localStorage.setItem(TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  },

  clearTokens(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

/**
 * Make an authenticated API request.
 *
 * Automatically attaches the Bearer token and handles token refresh
 * on 401 responses.
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const token = tokenStorage.getAccessToken();

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle 401 - try token refresh
  if (response.status === 401 && token) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      // Retry with new token
      const newToken = tokenStorage.getAccessToken();
      const retryHeaders: HeadersInit = {
        "Content-Type": "application/json",
        ...(newToken ? { Authorization: `Bearer ${newToken}` } : {}),
        ...options.headers,
      };
      const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: retryHeaders,
      });
      return handleResponse<T>(retryResponse);
    }
    // Refresh failed - clear tokens and redirect to login
    tokenStorage.clearTokens();
    if (typeof window !== "undefined") {
      window.location.href = "/auth/login";
    }
    throw new ApiError(401, "Authentication required");
  }

  return handleResponse<T>(response);
}

/** Handle API response and extract data. */
async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
  const data = await response.json();

  if (!response.ok || data.code !== 0) {
    throw new ApiError(
      data.code || response.status,
      data.message || "Request failed",
      data.data,
    );
  }

  return data as ApiResponse<T>;
}

/** Attempt to refresh the access token. */
async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return false;

    const data = await response.json();
    if (data.code === 0 && data.data) {
      tokenStorage.setTokens(data.data);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/** API client with typed methods. */
export const api = {
  /** GET request. */
  get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return request<T>(endpoint, { method: "GET" });
  },

  /** POST request with JSON body. */
  post<T>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> {
    return request<T>(endpoint, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  /** PUT request with JSON body. */
  put<T>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> {
    return request<T>(endpoint, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  /** DELETE request. */
  delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return request<T>(endpoint, { method: "DELETE" });
  },

  /** Upload file with FormData. */
  async upload<T>(endpoint: string, formData: FormData): Promise<ApiResponse<T>> {
    const token = tokenStorage.getAccessToken();
    const headers: HeadersInit = token
      ? { Authorization: `Bearer ${token}` }
      : {};

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers,
      body: formData,
    });

    return handleResponse<T>(response);
  },

  /** Stream SSE response for Q&A. */
  async *stream(
    endpoint: string,
    body: unknown,
  ): AsyncGenerator<string, void, unknown> {
    const token = tokenStorage.getAccessToken();
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok || !response.body) {
      throw new ApiError(response.status, "Stream request failed");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        yield decoder.decode(value, { stream: true });
      }
    } finally {
      reader.releaseLock();
    }
  },
};
