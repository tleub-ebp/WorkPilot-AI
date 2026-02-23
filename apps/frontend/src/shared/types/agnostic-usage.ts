/**
 * Agnostic Usage Types - Provider-agnostic usage data structures
 * 
 * These types allow any provider (Anthropic, OpenAI, Copilot, etc.) with any auth method
 * (OAuth, API Key) to be handled uniformly in the UI.
 */

/**
 * Base usage metrics that apply to all providers
 */
export interface BaseUsageMetrics {
  /** Session usage percentage (0-100) */
  sessionPercent: number;
  /** Weekly/monthly usage percentage (0-100) */
  periodicPercent: number;
  /** When the session limit resets */
  sessionResetTime?: string;
  /** When the periodic limit resets */
  periodicResetTime?: string;
  /** ISO timestamp of session reset */
  sessionResetTimestamp?: string;
  /** ISO timestamp of periodic reset */
  periodicResetTimestamp?: string;
  /** Raw session usage value */
  sessionUsageValue?: number;
  /** Session usage limit */
  sessionUsageLimit?: number;
  /** Raw periodic usage value */
  periodicUsageValue?: number;
  /** Periodic usage limit */
  periodicUsageLimit?: number;
}

/**
 * Provider-specific usage details
 */
export interface ProviderSpecificDetails {
  /** Anthropic-specific details */
  anthropic?: {
    subscriptionType?: string;
    rateLimitTier?: string;
    opusUsagePercent?: number;
  };
  
  /** OpenAI-specific details */
  openai?: {
    completions?: any;
    cost?: any;
    embeddings?: any;
    moderations?: any;
    estimatedCost?: number;
  };
  
  /** GitHub Copilot-specific details */
  copilot?: {
    totalTokens?: number;
    suggestionsCount?: number;
    acceptancesCount?: number;
    acceptanceRate?: number;
    estimatedCost?: number;
    periodDays?: number;
  };
  
  /** Generic provider details */
  generic?: {
    [key: string]: any;
  };
}

/**
 * Error information for failed usage fetching
 */
export interface UsageError {
  code: string;
  message: string;
  suggestions?: string[];
  provider?: string;
  requiresAction?: boolean;
  actionType?: 'reauth' | 'permission' | 'configuration' | 'retry';
}

/**
 * Agnostic usage data structure
 */
export interface AgnosticUsageData {
  /** Provider identifier */
  provider: string;
  /** Profile information */
  profileId: string;
  profileName: string;
  profileEmail?: string;
  
  /** Base metrics (common to all providers) */
  metrics: BaseUsageMetrics;
  
  /** Provider-specific details */
  details?: ProviderSpecificDetails;
  
  /** Error information if usage fetch failed */
  error?: UsageError;
  
  /** Authentication status */
  isAuthenticated: boolean;
  /** Whether re-authentication is needed */
  needsReauthentication: boolean;
  /** Whether the profile is rate limited */
  isRateLimited: boolean;
  /** Type of rate limit if limited */
  rateLimitType?: 'session' | 'periodic';
  
  /** Metadata */
  fetchedAt: Date;
  /** Usage window labels */
  usageWindows?: {
    sessionWindowLabel: string;
    periodicWindowLabel: string;
  };
}

/**
 * Provider configuration for UI rendering
 */
export interface ProviderConfig {
  /** Provider identifier */
  id: string;
  /** Display name */
  name: string;
  /** Icon name (from lucide-react) */
  icon: string;
  /** Color theme */
  color: string;
  /** Background color */
  bgColor: string;
  /** Border color */
  borderColor: string;
  /** Whether this provider supports OAuth */
  supportsOAuth: boolean;
  /** Whether this provider supports API keys */
  supportsApiKey: boolean;
  /** Default display format */
  defaultDisplayFormat: 'percentage' | 'tokens' | 'cost' | 'custom';
  /** Custom formatter function name */
  customFormatter?: string;
}

/**
 * Registry of all supported providers
 */
export const PROVIDER_REGISTRY: Record<string, ProviderConfig> = {
  anthropic: {
    id: 'anthropic',
    name: 'Anthropic Claude',
    icon: 'Activity',
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/20',
    supportsOAuth: true,
    supportsApiKey: true,
    defaultDisplayFormat: 'percentage'
  },
  openai: {
    id: 'openai',
    name: 'OpenAI',
    icon: 'TrendingUp',
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/20',
    supportsOAuth: false,
    supportsApiKey: true,
    defaultDisplayFormat: 'cost'
  },
  copilot: {
    id: 'copilot',
    name: 'GitHub Copilot',
    icon: 'TrendingUp',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20',
    supportsOAuth: true,
    supportsApiKey: false,
    defaultDisplayFormat: 'tokens'
  },
  ollama: {
    id: 'ollama',
    name: 'Ollama',
    icon: 'Activity',
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/20',
    supportsOAuth: false,
    supportsApiKey: false,
    defaultDisplayFormat: 'percentage'
  },
  generic: {
    id: 'generic',
    name: 'Generic Provider',
    icon: 'Activity',
    color: 'text-gray-500',
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/20',
    supportsOAuth: false,
    supportsApiKey: true,
    defaultDisplayFormat: 'percentage'
  }
};

/**
 * Get provider configuration by ID
 */
export function getProviderConfig(providerId: string): ProviderConfig {
  return PROVIDER_REGISTRY[providerId] || PROVIDER_REGISTRY.generic;
}

/**
 * Check if a provider supports a specific auth method
 */
export function supportsAuthMethod(providerId: string, method: 'oauth' | 'api_key'): boolean {
  const config = getProviderConfig(providerId);
  return method === 'oauth' ? config.supportsOAuth : config.supportsApiKey;
}
