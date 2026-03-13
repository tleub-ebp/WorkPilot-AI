/**
 * Provider Detection Utilities
 *
 * Detects API provider type from baseUrl patterns.
 * Mirrors the logic from usage-monitor.ts for use in renderer process.
 *
 * NOTE: Keep this in sync with usage-monitor.ts provider detection logic
 */

/**
 * API Provider type for usage monitoring
 * Determines which usage endpoint to query and how to normalize responses
 */
export type ApiProvider = 'anthropic' | 'openai' | 'ollama' | 'ollama_local' | 'copilot' | 'windsurf' | 'unknown';

/**
 * Provider detection patterns
 * Maps baseUrl patterns to provider types
 */
interface ProviderPattern {
  provider: ApiProvider;
  domainPatterns: string[];
}

const PROVIDER_PATTERNS: readonly ProviderPattern[] = [
  {
    provider: 'anthropic',
    domainPatterns: ['api.anthropic.com']
  },
  {
    provider: 'openai',
    domainPatterns: ['api.openai.com']
  },
  {
    provider: 'ollama',
    domainPatterns: ['ollama.ai', 'api.ollama.ai']
  },
  {
    provider: 'ollama_local',
    domainPatterns: ['localhost', '127.0.0.1']
  },
  {
    provider: 'copilot',
    domainPatterns: ['github.com', 'api.github.com']
  },
  {
    provider: 'windsurf',
    domainPatterns: ['codeium.com', 'server.codeium.com', 'api.codeium.com', 'api.windsurf.com', 'windsurf.ai']
  }
] as const;

/**
 * Detect API provider from baseUrl
 * Extracts domain and matches against known provider patterns
 *
 * @param baseUrl - The API base URL (e.g., 'https://api.anthropic.com')
 * @returns The detected provider type ('anthropic' | 'openai' | 'ollama' | 'ollama_local' | 'unknown')
 *
 * @example
 * detectProvider('https://api.anthropic.com') // returns 'anthropic'
 * detectProvider('https://api.openai.com') // returns 'openai'
 * detectProvider('http://localhost:11434') // returns 'ollama_local'
 * detectProvider('https://unknown.com/api') // returns 'unknown'
 */
export function detectProvider(baseUrl: string): ApiProvider {
  try {
    // Extract domain from URL
    const url = new URL(baseUrl);
    const domain = url.hostname;

    // Match against provider patterns
    for (const pattern of PROVIDER_PATTERNS) {
      for (const patternDomain of pattern.domainPatterns) {
        if (domain === patternDomain || domain.endsWith(`.${patternDomain}`)) {
          return pattern.provider;
        }
      }
    }

    // No match found
    return 'unknown';
  } catch (_error) {
    // Invalid URL format
    return 'unknown';
  }
}

/**
 * Get human-readable provider label
 *
 * @param provider - The provider type
 * @returns Display label for the provider
 */
export function getProviderLabel(provider: ApiProvider): string {
  switch (provider) {
    case 'anthropic':
      return 'Anthropic';
    case 'openai':
      return 'OpenAI';
    case 'ollama':
      return 'Ollama';
    case 'ollama_local':
      return 'Ollama (Local)';
    case 'copilot':
      return 'GitHub Copilot';
    case 'windsurf':
      return 'Windsurf (Codeium)';
    case 'unknown':
      return 'Unknown';
  }
}

/**
 * Get provider badge color scheme
 *
 * @param provider - The provider type
 * @returns CSS classes for badge styling
 */
export function getProviderBadgeColor(provider: ApiProvider): string {
  switch (provider) {
    case 'anthropic':
      return 'bg-orange-500/10 text-orange-500 border-orange-500/20 hover:bg-orange-500/15';
    case 'openai':
      return 'bg-green-500/10 text-green-500 border-green-500/20 hover:bg-green-500/15';
    case 'ollama':
      return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hover:bg-emerald-500/15';
    case 'ollama_local':
      return 'bg-teal-500/10 text-teal-500 border-teal-500/20 hover:bg-teal-500/15';
    case 'copilot':
      return 'bg-purple-500/10 text-purple-500 border-purple-500/20 hover:bg-purple-500/15';
    case 'windsurf':
      return 'bg-teal-400/10 text-teal-400 border-teal-400/20 hover:bg-teal-400/15';
    case 'unknown':
      return 'bg-gray-500/10 text-gray-500 border-gray-500/20 hover:bg-gray-500/15';
  }
}