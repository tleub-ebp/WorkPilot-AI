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
 * Special handling for Windsurf: OAuth status from backend.
 */
export async function getStaticProviders(profiles: APIProfile[] = []): Promise<ProvidersResponse> {
  const allProviders = providerRegistry.getAllProviders()
    .filter((p) => p.name !== 'claude' && p.name !== 'custom');

  const providers: CanonicalProvider[] = allProviders.map((p) => ({
    name: p.name,
    label: p.label,
    description: p.description,
  }));

  // Determine which providers have a configured profile
  const status: Record<string, boolean> = {};
  
  // Check Windsurf status from backend
  let windsurfStatus = false;
  try {
    const response = await fetch(`${API_BASE}/providers/windsurf/status`);
    if (response.ok) {
      const data = await response.json();
      windsurfStatus = data.available && data.authenticated;
    }
  } catch (error) {
    console.warn('Failed to fetch Windsurf status:', error);
  }

  for (const p of allProviders) {
    // Utiliser la même logique de détection que ProviderRegistry
    const hasProfile = profiles.some((prof) => {
      if (!prof.baseUrl) return false;
      
      // Logique de détection identique à ProviderRegistry.detectProviderFromProfile
      if (p.name === 'anthropic') {
        return prof.baseUrl?.includes('anthropic.com') || prof.name?.toLowerCase().includes('claude');
      }
      if (p.name === 'openai') {
        return prof.baseUrl?.includes('openai.com') || prof.name?.toLowerCase().includes('openai');
      }
      if (p.name === 'google') {
        return prof.baseUrl?.includes('google.com') || prof.name?.toLowerCase().includes('gemini');
      }
      if (p.name === 'meta') {
        return prof.baseUrl?.includes('meta.com') || prof.name?.toLowerCase().includes('llama');
      }
      if (p.name === 'mistral') {
        return prof.baseUrl?.includes('mistral.ai') || prof.name?.toLowerCase().includes('mistral');
      }
      if (p.name === 'deepseek') {
        return prof.baseUrl?.includes('deepseek.com') || prof.name?.toLowerCase().includes('deepseek');
      }
      if (p.name === 'windsurf') {
        // Windsurf est OAuth-only, vérifier via le statut du backend
        return false; // Le statut sera déterminé par le backend
      }
      
      // Fallback sur detectProvider pour les autres
      return detectProvider(prof.baseUrl) === p.name;
    });

    if (p.name === 'copilot') {
      status[p.name] = true;
    } else if (p.name === 'windsurf') {
      status[p.name] = windsurfStatus;
    } else {
      status[p.name] = hasProfile;
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
