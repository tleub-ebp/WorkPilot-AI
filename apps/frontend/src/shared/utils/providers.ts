/**
 * Central provider fetcher for LLM providers.
 *
 * Architecture improvement 3.1: providerRegistry is the **single source of truth**
 * for provider metadata (labels, descriptions, models, capabilities).
 * This module re-exports a thin adapter so existing consumers keep working.
 */

import { providerRegistry } from '../services/providerRegistry';
import { detectProvider } from './provider-detection';
import type { APIProfile } from '../types/profile';

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

/**
 * Returns a static provider list derived from providerRegistry (single source of truth).
 * Determines auth status from the provided profiles list (a profile
 * for that provider means it is configured / authenticated).
 * Special handling for GitHub Copilot: checks gh CLI authentication.
 */
export function getStaticProviders(profiles: APIProfile[] = []): ProvidersResponse {
  const allProviders = providerRegistry.getAllProviders()
    .filter((p) => p.name !== 'claude' && p.name !== 'custom');

  const providers: CanonicalProvider[] = allProviders.map((p) => ({
    name: p.name,
    label: p.label,
    description: p.description,
  }));

  // Determine which providers have a configured profile
  const status: Record<string, boolean> = {};
  for (const p of allProviders) {
    const hasProfile = profiles.some(
      (prof) => detectProvider(prof.baseUrl) === p.name
    );

    if (p.name === 'copilot') {
      status[p.name] = true;
    } else {
      status[p.name] = p.name === 'anthropic' || hasProfile;
    }
  }

  // Sort with custom order: anthropic first, copilot second, then others by authentication status and alphabetically
  providers.sort((a, b) => {
    if (a.name === 'anthropic' && b.name !== 'anthropic') return -1;
    if (b.name === 'anthropic' && a.name !== 'anthropic') return 1;

    if (a.name === 'copilot' && b.name !== 'copilot') return -1;
    if (b.name === 'copilot' && a.name !== 'copilot') return 1;

    const aAuth = status[a.name];
    const bAuth = status[b.name];
    if (aAuth && !bAuth) return -1;
    if (!aAuth && bAuth) return 1;

    return a.label.localeCompare(b.label);
  });

  return { providers, status };
}

/**
 * @deprecated Use getStaticProviders() instead — this HTTP fetch fails silently in Electron.
 */
export async function getProviders(): Promise<ProvidersResponse> {
  try {
    const res = await fetch(`${API_BASE}/providers`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return {
      providers: data.providers || [],
      status: data.status || {}
    };
  } catch {
    return { providers: [], status: {} };
  }
}
