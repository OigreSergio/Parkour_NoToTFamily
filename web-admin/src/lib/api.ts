/**
 * Minimal typed client for the FastAPI backend, used by the admin dashboard.
 *
 * Auth: JWT bearer tokens from `POST /api/v1/auth/login`, kept in
 * localStorage. Admin-only endpoints live under `/api/v1/admin/*` and the
 * backend enforces the admin role server-side (`require_admin`).
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const ACCESS_KEY = 'pk_admin_access_token';
const REFRESH_KEY = 'pk_admin_refresh_token';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface Spot {
  id: string;
  name: string;
  description: string;
  location: { lat: number; lng: number };
  photo_urls: string[];
  difficulty: number;
  status: 'pending' | 'verified' | 'rejected';
  submitted_by: string | null;
  verified_at: string | null;
  created_at: string;
}

export function saveTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function accessToken(): string | null {
  return typeof window === 'undefined' ? null : localStorage.getItem(ACCESS_KEY);
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  if (options.auth !== false) {
    const token = accessToken();
    if (!token) throw new Error('Unauthorized — please sign in');
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (res.status === 401 || res.status === 403) {
    throw new Error('Unauthorized — admin access required');
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = (await res.json()) as { detail?: unknown };
      if (typeof data.detail === 'string') detail = data.detail;
    } catch {
      // non-JSON error body — keep the status code message
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenPair>('/api/v1/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    }),

  /** Moderation queue — spots awaiting review (admin only). */
  pendingSpots: () => request<Spot[]>('/api/v1/admin/spots'),

  verifySpot: (id: string) =>
    request<Spot>(`/api/v1/admin/spots/${id}/verify`, { method: 'POST' }),

  rejectSpot: (id: string, reason: string) =>
    request<Spot>(`/api/v1/admin/spots/${id}/reject`, {
      method: 'POST',
      body: { reason },
    }),
};
