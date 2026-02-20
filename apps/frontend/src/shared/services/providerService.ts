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
      const response = await fetch('/configured_providers.json');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      return data.providers || [];
    } catch (error) {
      console.warn('[ProviderService] Failed to load providers from file, using providerRegistry fallback:', error);
      return this.getFallbackProviders();
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
      const fs = await import('node:fs/promises');
      const path = await import('node:path');
      const configPath = path.resolve(process.env.HOME || process.env.USERPROFILE || '', '.work_pilot_ai_llm_providers.json');
      
      let allConfigs: Record<string, ProviderConfig> = {};
      if (await fs.access(configPath).then(() => true).catch(() => false)) {
        try {
          const data = await fs.readFile(configPath, 'utf-8');
          allConfigs = JSON.parse(data);
        } catch {
          // Ignorer les erreurs de lecture
        }
      }
      
      // Fusionner avec la configuration existante
      allConfigs[provider] = { ...(allConfigs[provider]), ...config };
      await fs.writeFile(configPath, JSON.stringify(allConfigs, null, 2), 'utf-8');
    } catch (error) {
      console.error('[ProviderService] Failed to save user provider config:', error);
      throw error;
    }
  }

  /**
   * Récupère la configuration utilisateur d'un provider
   */
  async getUserProviderConfig(provider: string): Promise<ProviderConfig | null> {
    try {
      const fs = await import('node:fs/promises');
      const path = await import('node:path');
      const configPath = path.resolve(process.env.HOME || process.env.USERPROFILE || '', '.work_pilot_ai_llm_providers.json');
      
      if (!(await fs.access(configPath).then(() => true).catch(() => false))) {
        return null;
      }
      
      const data = await fs.readFile(configPath, 'utf-8');
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
