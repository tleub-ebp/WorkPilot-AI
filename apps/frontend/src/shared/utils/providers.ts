// Central provider fetcher for LLM providers
// Usage: import { getProviders, CanonicalProvider } from './providers';

import { PROVIDER_MODELS_MAP } from '../constants/models';
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

/** Human-readable label for each canonical provider */
const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic (Claude)',
  openai: 'OpenAI',
  google: 'Google Gemini',
  mistral: 'Mistral AI',
  deepseek: 'DeepSeek',
  meta: 'Meta (LLaMA)',
  aws: 'AWS Bedrock',
  ollama: 'Ollama (Local)',
};

/** Human-readable description for each canonical provider */
const PROVIDER_DESCRIPTIONS: Record<string, string> = {
  anthropic: 'Claude models via Anthropic API',
  openai: 'GPT and o-series models via OpenAI API',
  google: 'Gemini models via Google AI',
  mistral: 'Mistral models via Mistral AI API',
  deepseek: 'DeepSeek models via DeepSeek API',
  meta: 'LLaMA models via Meta API / Replicate',
  aws: 'Models via AWS Bedrock',
  ollama: 'Locally hosted models via Ollama',
};

/**
 * Returns a static provider list derived from PROVIDER_MODELS_MAP.
 * Determines auth status from the provided profiles list (a profile
 * for that provider means it is configured / authenticated).
 *
 * This replaces the previous HTTP fetch to /providers which failed
 * silently in Electron where no HTTP server is running.
 */
export function getStaticProviders(profiles: APIProfile[] = []): ProvidersResponse {
  // Build canonical provider list from the model map, excluding the 'claude' alias
  const providerNames = Object.keys(PROVIDER_MODELS_MAP).filter(
    (name) => name !== 'claude'
  );

  const providers: CanonicalProvider[] = providerNames.map((name) => ({
    name,
    label: PROVIDER_LABELS[name] ?? name.charAt(0).toUpperCase() + name.slice(1),
    description: PROVIDER_DESCRIPTIONS[name] ?? '',
  }));

  // Determine which providers have a configured profile
  const status: Record<string, boolean> = {};
  for (const name of providerNames) {
    const hasProfile = profiles.some(
      (p) => detectProvider(p.baseUrl) === name
    );
    // anthropic is always considered available (OAuth / Claude Code subscription)
    status[name] = name === 'anthropic' || hasProfile;
  }

  // Sort: anthropic first, then rest alphabetically
  providers.sort((a, b) => {
    if (a.name === 'anthropic') return -1;
    if (b.name === 'anthropic') return 1;
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
