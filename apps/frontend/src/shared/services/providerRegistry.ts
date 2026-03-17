/**
 * Provider Registry - Service centralisé pour la gestion des providers LLM
 * Point d'entrée unique pour backend et frontend
 */

import { PROVIDER_MODELS_MAP } from '../constants/models';
import type { APIProfile } from '../types/profile';

export interface Provider {
  name: string;
  label: string;
  description: string;
  icon?: string; // Chemin vers l'icône ou composant React
  category: 'anthropic' | 'openai' | 'google' | 'meta' | 'aws' | 'local' | 'special';
  requiresApiKey: boolean;
  requiresOAuth: boolean;
  requiresCLI: boolean;
  models: Array<{
    value: string;
    label: string;
    tier: 'flagship' | 'standard' | 'fast' | 'local';
    supportsThinking?: boolean;
  }>;
}

export interface ProviderStatus {
  available: boolean;
  authenticated: boolean;
  error?: string;
  lastChecked?: Date;
}

export interface ProvidersResponse {
  providers: Provider[];
  status: Record<string, ProviderStatus>;
}

/**
 * Registre central des providers LLM
 */
class ProviderRegistry {
  private static instance: ProviderRegistry;
  private readonly providers: Map<string, Provider> = new Map();

  private constructor() {
    this.initializeProviders();
  }

  public static getInstance(): ProviderRegistry {
    if (!ProviderRegistry.instance) {
      ProviderRegistry.instance = new ProviderRegistry();
    }
    return ProviderRegistry.instance;
  }

  private initializeProviders(): void {
    // --- Anthropic (Claude) ---
    this.providers.set('anthropic', {
      name: 'anthropic',
      label: 'Anthropic (Claude)',
      description: 'Claude models via Anthropic API',
      category: 'anthropic',
      requiresApiKey: true,
      requiresOAuth: true,
      requiresCLI: false,
      models: PROVIDER_MODELS_MAP.anthropic || []
    });

    // --- OpenAI ---
    this.providers.set('openai', {
      name: 'openai',
      label: 'OpenAI (ChatGPT)',
      description: 'GPT and o-series models via OpenAI API',
      category: 'openai',
      requiresApiKey: true,
      requiresOAuth: true,
      requiresCLI: false,
      models: PROVIDER_MODELS_MAP.openai || []
    });

    // --- Google Gemini ---
    this.providers.set('google', {
      name: 'google',
      label: 'Google (Gemini)',
      description: 'Gemini models via Google AI',
      category: 'google',
      requiresApiKey: true,
      requiresOAuth: false,
      requiresCLI: false,
      models: PROVIDER_MODELS_MAP.google || []
    });

    // --- Meta (LLaMA) ---
    this.providers.set('meta', {
      name: 'meta',
      label: 'Meta (LLaMA)',
      description: 'LLaMA models via Meta API / Replicate',
      category: 'meta',
      requiresApiKey: true,
      requiresOAuth: false,
      requiresCLI: false,
      models: PROVIDER_MODELS_MAP.meta || []
    });

    // --- Mistral AI ---
    this.providers.set('mistral', {
      name: 'mistral',
      label: 'Mistral AI',
      description: 'Mistral models via Mistral AI API',
      category: 'special',
      requiresApiKey: true,
      requiresOAuth: false,
      requiresCLI: false,
      models: PROVIDER_MODELS_MAP.mistral || []
    });

    // --- DeepSeek ---
    this.providers.set('deepseek', {
      name: 'deepseek',
      label: 'DeepSeek',
      description: 'DeepSeek models via DeepSeek API',
      category: 'special',
      requiresApiKey: true,
      requiresOAuth: false,
      requiresCLI: false,
      models: PROVIDER_MODELS_MAP.deepseek || []
    });

    // --- AWS Bedrock ---
    this.providers.set('aws', {
      name: 'aws',
      label: 'AWS (Bedrock)',
      description: 'Models via AWS Bedrock',
      category: 'aws',
      requiresApiKey: true,
      requiresOAuth: false,
      requiresCLI: false,
      models: PROVIDER_MODELS_MAP.aws || []
    });

    // --- GitHub Copilot ---
    this.providers.set('copilot', {
      name: 'copilot',
      label: 'GitHub Copilot',
      description: 'GitHub Copilot CLI models (gh copilot)',
      category: 'special',
      requiresApiKey: false,
      requiresOAuth: false,
      requiresCLI: true, // Requiert gh CLI
      models: PROVIDER_MODELS_MAP.copilot || []
    });

    // --- Grok (xAI) ---
    this.providers.set('grok', {
      name: 'grok',
      label: 'Grok (xAI)',
      description: 'Grok models via xAI',
      category: 'special',
      requiresApiKey: true,
      requiresOAuth: false,
      requiresCLI: false,
      models: [
        { value: 'grok-2', label: 'Grok 2', tier: 'flagship', supportsThinking: true },
        { value: 'grok-2-mini', label: 'Grok 2 Mini', tier: 'standard' },
        { value: 'grok-beta', label: 'Grok Beta', tier: 'fast' }
      ]
    });

    // --- Custom/Enterprise ---
    this.providers.set('custom', {
      name: 'custom',
      label: 'Custom/Enterprise',
      description: 'Custom API endpoints',
      category: 'special',
      requiresApiKey: true,
      requiresOAuth: false,
      requiresCLI: false,
      models: PROVIDER_MODELS_MAP.custom || []
    });

    // --- Windsurf ---
    this.providers.set('windsurf', {
      name: 'windsurf',
      label: 'Windsurf (Codeium)',
      description: 'AI-powered coding assistant by Codeium',
      category: 'special',
      requiresApiKey: true,
      requiresOAuth: false,
      requiresCLI: false,
      models: [
        { value: 'windsurf-default', label: 'Windsurf Default', tier: 'standard' },
        { value: 'windsurf-premier', label: 'Windsurf Premier', tier: 'flagship' },
        { value: 'windsurf-cascade', label: 'Windsurf Cascade', tier: 'flagship', supportsThinking: true },
        { value: 'gpt-4o', label: 'GPT-4o', tier: 'flagship' },
        { value: 'claude-3.5-sonnet', label: 'Claude 3.5 Sonnet', tier: 'flagship' }
      ]
    });

    // --- Cursor ---
    this.providers.set('cursor', {
      name: 'cursor',
      label: 'Cursor IDE',
      description: 'AI-first VS Code fork with advanced features',
      category: 'special',
      requiresApiKey: true,
      requiresOAuth: false,
      requiresCLI: false,
      models: [
        { value: 'cursor-default', label: 'Cursor Default', tier: 'standard' },
        { value: 'cursor-pro', label: 'Cursor Pro', tier: 'flagship' },
        { value: 'gpt-4o', label: 'GPT-4o', tier: 'flagship' },
        { value: 'gpt-4-turbo', label: 'GPT-4 Turbo', tier: 'standard' },
        { value: 'claude-3.5-sonnet', label: 'Claude 3.5 Sonnet', tier: 'flagship' },
        { value: 'claude-3-opus', label: 'Claude 3 Opus', tier: 'flagship' }
      ]
    });

    // --- Ollama (Local) ---
    this.providers.set('ollama', {
      name: 'ollama',
      label: 'Ollama (Local)',
      description: 'Locally hosted models via Ollama',
      category: 'local',
      requiresApiKey: false,
      requiresOAuth: false,
      requiresCLI: false,
      models: PROVIDER_MODELS_MAP.ollama || []
    });
  }

  /**
   * Récupère tous les providers disponibles
   */
  public getAllProviders(): Provider[] {
    return Array.from(this.providers.values());
  }

  /**
   * Récupère un provider par son nom
   */
  public getProvider(name: string): Provider | undefined {
    return this.providers.get(name);
  }

  /**
   * Vérifie le statut d'authentification d'un provider
   */
  public async checkProviderStatus(name: string, profiles: APIProfile[] = []): Promise<ProviderStatus> {
    const provider = this.getProvider(name);
    if (!provider) {
      return {
        available: false,
        authenticated: false,
        error: `Provider ${name} not found`
      };
    }

    const status: ProviderStatus = {
      available: true,
      authenticated: false,
      lastChecked: new Date()
    };

    try {
      // Cas spécial pour Anthropic (toujours disponible via OAuth/Claude Code)
      if (name === 'anthropic') {
        status.authenticated = true;
        return status;
      }

      // Cas spécial pour GitHub Copilot (vérification gh CLI)
      if (name === 'copilot' && provider.requiresCLI) {
        if (typeof globalThis !== 'undefined' && globalThis.electronAPI) {
          // Dans Electron, utiliser Node.js pour vérifier gh CLI
          const isAuthenticated = await globalThis.electronAPI.checkCopilotAuth();
          status.authenticated = isAuthenticated;
        } else {
          // Fallback dans le navigateur (assume disponible pour le développement)
          status.authenticated = true;
        }
        return status;
      }

      // Vérification basique pour les autres providers
      if (provider.requiresApiKey) {
        const hasProfile = profiles.some(p => this.detectProviderFromProfile(p) === name);
        status.authenticated = hasProfile;
      }

      if (provider.requiresOAuth) {
        // Logique OAuth spécifique au provider
        status.authenticated = this.checkOAuthStatus(name);
      }

    } catch (error) {
      status.error = error instanceof Error ? error.message : 'Unknown error';
      status.authenticated = false;
    }

    return status;
  }

  /**
   * Vérifie le statut de tous les providers
   */
  public async checkAllProvidersStatus(profiles: APIProfile[] = []): Promise<Record<string, ProviderStatus>> {
    const providers = this.getAllProviders();
    const status: Record<string, ProviderStatus> = {};

    for (const provider of providers) {
      status[provider.name] = await this.checkProviderStatus(provider.name, profiles);
    }

    return status;
  }

  /**
   * Détecte le provider à partir d'un profil
   */
  private detectProviderFromProfile(profile: APIProfile): string {
    // Logique de détection existante
    if (profile.baseUrl?.includes('anthropic.com') || profile.name?.toLowerCase().includes('claude')) {
      return 'anthropic';
    }
    if (profile.baseUrl?.includes('openai.com') || profile.name?.toLowerCase().includes('openai')) {
      return 'openai';
    }
    if (profile.baseUrl?.includes('google.com') || profile.name?.toLowerCase().includes('gemini')) {
      return 'google';
    }
    if (profile.baseUrl?.includes('meta.com') || profile.name?.toLowerCase().includes('llama')) {
      return 'meta';
    }
    if (profile.baseUrl?.includes('mistral.ai') || profile.name?.toLowerCase().includes('mistral')) {
      return 'mistral';
    }
    if (profile.baseUrl?.includes('deepseek.com') || profile.name?.toLowerCase().includes('deepseek')) {
      return 'deepseek';
    }
    if (profile.baseUrl?.includes('aws.amazon.com') || profile.name?.toLowerCase().includes('bedrock')) {
      return 'aws';
    }
    if (profile.baseUrl?.includes('ollama') || profile.name?.toLowerCase().includes('ollama')) {
      return 'ollama';
    }
    if (profile.baseUrl?.includes('x.ai') || profile.name?.toLowerCase().includes('grok')) {
      return 'grok';
    }
    if (profile.baseUrl?.includes('codeium.com') || profile.baseUrl?.includes('windsurf.com') || profile.baseUrl?.includes('windsurf.ai') || profile.name?.toLowerCase().includes('windsurf')) {
      return 'windsurf';
    }

    return 'custom';
  }

  /**
   * Vérifie le statut OAuth pour un provider
   */
  private checkOAuthStatus(providerName: string): boolean {
    // Logique OAuth spécifique
    if (providerName === 'anthropic') {
      // Vérifier le token Claude Code OAuth
      return typeof localStorage !== 'undefined' && 
             (localStorage.getItem('claude_oauth_token') || 
              localStorage.getItem('anthropic_api_key')) !== null;
    }
    
    return false;
  }

  /**
   * Ajoute dynamiquement un nouveau provider
   */
  public addProvider(provider: Provider): void {
    this.providers.set(provider.name, provider);
  }

  /**
   * Supprime un provider
   */
  public removeProvider(name: string): boolean {
    return this.providers.delete(name);
  }

  /**
   * Met à jour un provider existant
   */
  public updateProvider(name: string, updates: Partial<Provider>): boolean {
    const existing = this.providers.get(name);
    if (!existing) return false;

    const updated = { ...existing, ...updates };
    this.providers.set(name, updated);
    return true;
  }
}

// Export du singleton
export const providerRegistry = ProviderRegistry.getInstance();

// Fonctions utilitaires pour la compatibilité
export function getProviders(profiles: APIProfile[] = []): Promise<ProvidersResponse> {
  return providerRegistry.checkAllProvidersStatus(profiles).then(status => ({
    providers: providerRegistry.getAllProviders(),
    status
  }));
}

export function getProvider(name: string): Provider | undefined {
  return providerRegistry.getProvider(name);
}

export function getModelsForProvider(providerName: string): Provider['models'] {
  const provider = providerRegistry.getProvider(providerName);
  return provider?.models || [];
}
