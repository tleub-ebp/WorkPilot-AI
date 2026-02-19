/**
 * ProviderService - Service centralisé pour la gestion des providers LLM
 * 
 * Point d'entrée unique pour toutes les opérations sur les providers:
 * - Chargement depuis configured_providers.json
 * - Cache en mémoire pour éviter les rechargements
 * - Interfaces TypeScript fortes
 * - Fallback robuste en cas d'erreur
 */

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
      // Charger depuis le fichier statique servi par Vite
      const response = await fetch('/configured_providers.json');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      return data.providers || [];
    } catch (error) {
      console.warn('[ProviderService] Failed to load providers from file, using fallback:', error);
      return this.getFallbackProviders();
    }
  }

  /**
   * Fallback statique en cas d'échec total
   */
  private getFallbackProviders(): Provider[] {
    return [
      { name: 'anthropic', label: 'Anthropic (Claude)', description: 'Claude, focalisé sur la sécurité et l\'IA d\'entreprise.' },
      { name: 'openai', label: 'OpenAI', description: 'Créateur de la série GPT (ChatGPT, GPT-4/4o/5).' },
      { name: 'google', label: 'Google / Google DeepMind', description: 'Modèles Gemini.' },
      { name: 'meta', label: 'Meta (Facebook/Meta AI)', description: 'Modèles LLaMA et variantes open source.' },
      { name: 'mistral', label: 'Mistral AI', description: 'Startup française, LLM open weight et commercial.' },
      { name: 'deepseek', label: 'DeepSeek', description: 'Entreprise chinoise, agent conversationnel.' },
      { name: 'aws', label: 'Amazon Web Services (AWS)', description: 'Offre des API LLM intégrées à ses services cloud.' },
      { name: 'grok', label: 'Grok (xAI)', description: 'Modèles Grok via xAI, la société d\'Elon Musk.' },
      { name: 'ollama', label: 'LLM local (Ollama, LM Studio, etc.)', description: 'Exécutez un modèle LLM localement sur votre machine (Ollama, LM Studio, etc.).' },
      { name: 'copilot', label: 'GitHub Copilot', description: 'Assistant de code IA par GitHub, basé sur les modèles OpenAI et Claude.' }
    ];
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
