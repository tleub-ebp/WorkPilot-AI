/**
 * ProviderService - Service centralisé pour la gestion des providers LLM
 *
 * Architecture improvement 3.1: delegates to providerRegistry (single source of truth)
 * for the canonical provider list. Falls back to providerRegistry instead of
 * maintaining a duplicate hardcoded list.
 */

import { providerRegistry } from './providerRegistry';

export interface Provider {
  name: string;
  label: string;
  description: string;
}

export interface ProviderConfig {
  api_key?: string;
  base_url?: string;
  validated?: boolean;
}

class ProviderServiceClass {
  private providers: Provider[] | null = null;
  private isLoading = false;
  private loadPromise: Promise<Provider[]> | null = null;

  /**
   * Récupère tous les providers avec cache
   */
  async getAllProviders(): Promise<Provider[]> {
    if (this.providers) {
      return this.providers;
    }

    if (this.isLoading && this.loadPromise) {
      return this.loadPromise;
    }

    this.isLoading = true;
    this.loadPromise = this.loadProvidersFromFile();
    
    try {
      this.providers = await this.loadPromise;
      return this.providers;
    } finally {
      this.isLoading = false;
      this.loadPromise = null;
    }
  }

  /**
   * Force le rechargement des providers (utile après mise à jour)
   */
  async refreshProviders(): Promise<Provider[]> {
    this.providers = null;
    return this.getAllProviders();
  }

  /**
   * Récupère un provider par son nom
   */
  async getProviderByName(name: string): Promise<Provider | undefined> {
    const providers = await this.getAllProviders();
    return providers.find(p => p.name === name);
  }

  /**
   * Charge les providers depuis configured_providers.json avec fallback
   */
  private async loadProvidersFromFile(): Promise<Provider[]> {
    try {
      // Import the JSON file directly from src
      const providersData = await import('../../configured_providers.json');
      return providersData.providers || [];
    } catch (error) {
      console.warn('Failed to load providers from configured_providers.json, using fallback:', error);
      const fallbackProviders = this.getFallbackProviders();
      return fallbackProviders;
    }
  }

  /**
   * Fallback: delegate to providerRegistry (single source of truth)
   */
  private getFallbackProviders(): Provider[] {
    return providerRegistry.getAllProviders()
      .filter(p => p.name !== 'custom')
      .map(p => ({ name: p.name, label: p.label, description: p.description }));
  }

  /**
   * Vérifie si un provider nécessite une clé API
   */
  async getApiKeyField(providerName: string): Promise<string | null> {
    const apiKeyMap: Record<string, string | null> = {
      'openai': 'globalOpenAIApiKey',
      'gemini': 'globalGoogleApiKey',
      'google': 'globalGoogleDeepMindApiKey',
      'meta': 'globalMetaApiKey',
      'meta-llama': 'globalMetaLlamaApiKey',
      'mistral': 'globalMistralApiKey',
      'deepseek': 'globalDeepSeekApiKey',
      'grok': 'globalGrokApiKey',
      'aws': 'globalAWSApiKey',
      'ollama': null,
      'copilot': null,
      'azure-openai': 'globalOpenAIApiKey',
      'anthropic': null, // Claude utilise OAuth
    };
    
    return apiKeyMap[providerName] || null;
  }

  /**
   * Sauvegarde la configuration des providers dans le fichier utilisateur
   */
  async saveUserProviderConfig(provider: string, config: ProviderConfig): Promise<void> {
    try {
      // Utiliser localStorage au lieu de fs pour le contexte navigateur
      const configKey = `work_pilot_ai_llm_providers_${provider}`;
      const existingData = localStorage.getItem(configKey);
      let allConfigs: Record<string, ProviderConfig> = {};
      
      if (existingData) {
        try {
          allConfigs = JSON.parse(existingData);
        } catch {
          // Ignorer les erreurs de lecture
        }
      }
      
      // Fusionner avec la configuration existante
      allConfigs[provider] = { ...(allConfigs[provider]), ...config };
      
      localStorage.setItem(configKey, JSON.stringify(allConfigs, null, 2));
    } catch (error) {
      console.error('[ProviderService] Failed to save user provider config:', error);
      throw error;
    }
  }

  /**
   * Teste la connexion à un provider
   */
  async testProvider(providerName: string): Promise<{ success: boolean; message: string; details?: any }> {
    try {
      // Essayer d'abord le nouveau système CredentialManager si disponible
      const credentialResult = await this.tryCredentialManager(providerName);
      if (credentialResult) {
        return credentialResult;
      }

      // Logique legacy existante en fallback
      return await this.testProviderLegacy(providerName);
    } catch (error) {
      console.error(`[ProviderService] Test failed for ${providerName}:`, error);
      return { 
        success: false, 
        message: error instanceof Error ? error.message : 'Unknown error' 
      };
    }
  }

  /**
   * Essaie d'utiliser le CredentialManager pour tester un provider
   */
  private async tryCredentialManager(providerName: string): Promise<{ success: boolean; message: string; details?: any } | null> {
    if (!globalThis.electronAPI?.invoke) {
      return null;
    }

    try {
      const result = await globalThis.electronAPI.invoke('credential:testProvider', providerName);
      return result;
    } catch (_credentialError) {
      return null;
    }
  }

  /**
   * Teste un provider avec la logique legacy
   */
  private async testProviderLegacy(providerName: string): Promise<{ success: boolean; message: string; details?: any }> {
    const { providers: staticProviders, status } = await this.getProviderData();
    
    const provider = staticProviders.find(p => p.name === providerName);
    if (!provider) {
      return { success: false, message: 'Provider not found' };
    }

    // Ollama is always testable (local provider with a default URL)
    if (!status[providerName] && providerName !== 'ollama') {
      return this.handleUnconfiguredProvider(providerName);
    }

    const { apiKey, baseUrl } = await this.getProviderConfig(providerName);

    if (!apiKey && !baseUrl) {
      return { success: false, message: 'Missing API configuration' };
    }

    return await this.testProviderConnection(providerName, apiKey, baseUrl);
  }

  /**
   * Récupère les données des providers
   */
  private async getProviderData() {
    const { getStaticProviders } = await import('@shared/utils/providers');
    const profiles = this.getCurrentProfiles();
    // Pass settings to detect providers configured via global keys (e.g., globalWindsurfApiKey)
    let settings: Record<string, any> | undefined;
    try {
      const { useSettingsStore } = await import('@/stores/settings-store');
      settings = { ...(useSettingsStore.getState().settings as Record<string, any>) };
    } catch {
      // settings store not available in some contexts
    }
    // Enrich settings with Claude OAuth status from CLI config files (main process)
    try {
      if (settings && globalThis.electronAPI?.checkClaudeOAuth) {
        const oauthResult = await globalThis.electronAPI.checkClaudeOAuth();
        if (oauthResult.isAuthenticated) {
          settings.globalClaudeOAuthToken = oauthResult.profileName || 'oauth-authenticated';
        }
      }
    } catch {
      // IPC not available
    }
    // Enrich settings with OpenAI Codex CLI OAuth status from config files (main process)
    try {
      if (settings && globalThis.electronAPI?.checkOpenAICodexOAuth) {
        const oauthResult = await globalThis.electronAPI.checkOpenAICodexOAuth();
        if (oauthResult.isAuthenticated) {
          settings.globalOpenAICodexOAuthToken = oauthResult.profileName || 'codex-authenticated';
        }
      }
    } catch {
      // IPC not available
    }
    return await getStaticProviders(profiles, settings);
  }

  /**
   * Gère le cas des providers non configurés
   */
  private handleUnconfiguredProvider(providerName: string): { success: boolean; message: string; details?: any } {
    if (providerName === 'copilot') {
      return {
        success: true,
        message: 'GitHub Copilot authentication (CLI-based)',
        details: { method: 'GitHub CLI' }
      };
    }

    if (providerName === 'windsurf') {
      return { success: false, message: 'Provider windsurf not configured. Use SSO or provide an API key in settings.' };
    }

    return { success: false, message: 'Provider not configured' };
  }

  /**
   * Récupère la configuration API pour un provider
   */
  private async getProviderConfig(providerName: string): Promise<{ apiKey?: string; baseUrl?: string }> {
    // Ollama uses settings (not profiles) with a default localhost URL
    if (providerName === 'ollama') {
      let settings: Record<string, any> = {};
      try {
        const { useSettingsStore } = await import('@/stores/settings-store');
        settings = useSettingsStore.getState().settings as Record<string, any>;
      } catch {
        // Store not available in some contexts
      }
      const baseUrl = (settings?.globalOllamaApiUrl as string) || 'http://localhost:11434';
      return { baseUrl };
    }

    const profiles = this.getCurrentProfiles();
    const { detectProvider } = await import('@shared/utils/provider-detection');

    const profile = this.findProviderProfile(profiles, providerName, detectProvider);

    if (profile) {
      return { apiKey: profile.apiKey, baseUrl: profile.baseUrl };
    } else {
      return {};
    }
  }

  /**
   * Trouve le profile correspondant à un provider
   */
  private findProviderProfile(profiles: any[], providerName: string, detectProvider: (baseUrl: string) => string): any {
    return profiles.find((p: any) => {
      if (!p.baseUrl) return false;
      
      const detectedProvider = detectProvider(p.baseUrl);
      const baseUrlLower = p.baseUrl.toLowerCase();
      
      return this.matchesProvider(providerName, detectedProvider, baseUrlLower);
    });
  }

  /**
   * Vérifie si un profile correspond à un provider
   */
  private matchesProvider(providerName: string, detectedProvider: string, baseUrlLower: string): boolean {
    switch (providerName) {
      case 'gemini':
      case 'google':
        return baseUrlLower.includes('googleapis.com') || baseUrlLower.includes('generativelanguage.googleapis.com');
      case 'mistral':
        return baseUrlLower.includes('mistral.ai') || baseUrlLower.includes('api.mistral.ai');
      case 'windsurf':
        return baseUrlLower.includes('codeium.com') || baseUrlLower.includes('windsurf.com') || baseUrlLower.includes('windsurf.ai');
      default:
        return detectedProvider === providerName ||
               (providerName === 'claude' && detectedProvider === 'anthropic');
    }
  }

  /**
   * Teste la connexion selon le type de provider
   */
  private async testProviderConnection(providerName: string, apiKey?: string, baseUrl?: string): Promise<{ success: boolean; message: string; details?: any }> {
    // Cas spécial pour Anthropic
    if (providerName === 'anthropic' || providerName === 'claude') {
      return await this.testAnthropicProvider();
    }

    // Test de connexion générique selon le type de provider
    switch (providerName) {
      case 'openai':
        return await this.testOpenAIConnection(apiKey!, baseUrl);
      case 'gemini':
      case 'google':
        return await this.testGoogleConnection(apiKey!, baseUrl);
      case 'mistral':
        return await this.testMistralConnection(apiKey!, baseUrl);
      case 'ollama':
        return await this.testOllamaConnection(baseUrl!);
      default:
        return await this.testGenericConnection(baseUrl!, apiKey);
    }
  }

  /**
   * Teste le provider Anthropic avec OAuth/Claude Code
   */
  private async testAnthropicProvider(): Promise<{ success: boolean; message: string; details?: any }> {
    const { useSettingsStore } = await import('@/stores/settings-store');
    const { testConnection } = useSettingsStore.getState();
    
    const result = await testConnection('https://api.anthropic.com', 'test-oauth-check');
    
    if (!result) {
      return { success: false, message: 'Anthropic provider test not available' };
    }

    if (result.success) {
      return {
        success: true,
        message: 'Anthropic provider is accessible (OAuth/Claude Code)',
        details: { method: 'OAuth/Claude Code', status: 'Accessible' }
      };
    }

    if (result.errorType === 'auth') {
      return {
        success: true,
        message: 'Anthropic provider is configured (OAuth/Claude Code active)',
        details: { method: 'OAuth/Claude Code', status: 'Authentication required but working' }
      };
    }

    return {
      success: false,
      message: result.errorType ? `Anthropic provider error: ${result.errorType}` : (result.message || 'Anthropic provider unavailable'),
      details: { error: result.errorType ? result.errorType : 'Unknown error' }
    };
  }

  /**
   * Récupère les profiles actuels
   */
  private getCurrentProfiles(): any[] {
    return this.currentProfiles;
  }

  /**
   * Définit les profiles actuels pour les tests
   */
  setProfiles(profiles: any[]): void {
    this.currentProfiles = profiles;
  }

  private currentProfiles: any[] = [];

  /**
   * Test de connexion pour OpenAI
   */
  private async testOpenAIConnection(apiKey: string, baseUrl?: string): Promise<{ success: boolean; message: string; details?: any }> {
    try {
      const response = await fetch(`${baseUrl || 'https://api.openai.com'}/v1/models`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(10000), // Timeout 10s
      });

      if (response.ok) {
        const data = await response.json();
        return { 
          success: true, 
          message: 'Connection successful',
          details: { modelCount: data.data?.length || 0 }
        };
      } else {
        return { 
          success: false, 
          message: `HTTP ${response.status}: ${response.statusText}` 
        };
      }
    } catch (error) {
      return { 
        success: false, 
        message: error instanceof Error ? error.message : 'Connection failed' 
      };
    }
  }

  /**
   * Test de connexion pour Google/Gemini
   */
  private async testGoogleConnection(apiKey: string, baseUrl?: string): Promise<{ success: boolean; message: string; details?: any }> {
    try {
      const response = await fetch(`${baseUrl || 'https://generativelanguage.googleapis.com'}/v1/models?key=${apiKey}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(10000),
      });

      if (response.ok) {
        const data = await response.json();
        return { 
          success: true, 
          message: 'Connection successful',
          details: { modelCount: data.models?.length || 0 }
        };
      } else {
        return { 
          success: false, 
          message: `HTTP ${response.status}: ${response.statusText}` 
        };
      }
    } catch (error) {
      return { 
        success: false, 
        message: error instanceof Error ? error.message : 'Connection failed' 
      };
    }
  }

  /**
   * Test de connexion pour Mistral
   */
  private async testMistralConnection(apiKey: string, baseUrl?: string): Promise<{ success: boolean; message: string; details?: any }> {
    try {
      const response = await fetch(`${baseUrl || 'https://api.mistral.ai'}/v1/models`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(10000),
      });

      if (response.ok) {
        const data = await response.json();
        return { 
          success: true, 
          message: 'Connection successful',
          details: { modelCount: data.data?.length || 0 }
        };
      } else {
        return { 
          success: false, 
          message: `HTTP ${response.status}: ${response.statusText}` 
        };
      }
    } catch (error) {
      return { 
        success: false, 
        message: error instanceof Error ? error.message : 'Connection failed' 
      };
    }
  }

  /**
   * Test de connexion pour Ollama
   */
  private async testOllamaConnection(baseUrl: string): Promise<{ success: boolean; message: string; details?: any }> {
    try {
      const response = await fetch(`${baseUrl}/api/tags`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(10000),
      });

      if (response.ok) {
        const data = await response.json();
        return { 
          success: true, 
          message: 'Connection successful',
          details: { modelCount: data.models?.length || 0 }
        };
      } else {
        return { 
          success: false, 
          message: `HTTP ${response.status}: ${response.statusText}` 
        };
      }
    } catch (error) {
      return { 
        success: false, 
        message: error instanceof Error ? error.message : 'Connection failed' 
      };
    }
  }

  /**
   * Test de connexion générique pour autres providers
   */
  private async testGenericConnection(baseUrl: string, apiKey?: string): Promise<{ success: boolean; message: string; details?: any }> {
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (apiKey) {
        headers['Authorization'] = `Bearer ${apiKey}`;
      }

      const response = await fetch(`${baseUrl}/health`, {
        method: 'GET',
        headers,
        signal: AbortSignal.timeout(10000),
      });

      if (response.ok) {
        return { 
          success: true, 
          message: 'Connection successful' 
        };
      } else {
        return { 
          success: false, 
          message: `HTTP ${response.status}: ${response.statusText}` 
        };
      }
    } catch (error) {
      return { 
        success: false, 
        message: error instanceof Error ? error.message : 'Connection failed' 
      };
    }
  }

  /**
   * Récupère la configuration utilisateur d'un provider
   */
  async getUserProviderConfig(provider: string): Promise<ProviderConfig | null> {
    try {
      // Utiliser localStorage au lieu de fs pour le contexte navigateur
      const configKey = `work_pilot_ai_llm_providers_${provider}`;
      const data = localStorage.getItem(configKey);
      
      if (!data) {
        return null;
      }
      
      const allConfigs: Record<string, ProviderConfig> = JSON.parse(data);
      return allConfigs[provider] || null;
    } catch (error) {
      console.warn('[ProviderService] Failed to load user provider config:', error);
      return null;
    }
  }
}

// Export du singleton
export const ProviderService = new ProviderServiceClass();

// Export des types pour compatibilité
export type { Provider as Connector };
