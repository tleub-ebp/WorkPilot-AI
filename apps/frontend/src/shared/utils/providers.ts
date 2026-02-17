// Central provider fetcher for LLM providers
// Usage: import { getProviders, CanonicalProvider } from './providers';

export interface CanonicalProvider {
  name: string;
  label: string;
  description: string;
}

export const API_BASE =
  typeof import.meta !== "undefined" &&
  import.meta.env &&
  import.meta.env.VITE_BACKEND_URL
    ? import.meta.env.VITE_BACKEND_URL
    : "";

export interface ProvidersResponse {
  providers: CanonicalProvider[];
  status: Record<string, boolean>;
}

export async function getProviders(): Promise<ProvidersResponse> {
  try {
    const res = await fetch(`${API_BASE}/providers`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return {
      providers: data.providers || [],
      status: data.status || {}
    };
  } catch (err) {
    return { providers: [], status: {} };
  }
}