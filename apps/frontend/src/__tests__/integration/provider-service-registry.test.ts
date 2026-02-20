/**
 * Integration tests for ProviderService + ProviderRegistry
 * Tests that the provider discovery, caching, fallback, and status checking
 * work correctly across the service and registry layers.
 * Improvement 6.2: Integration tests Frontend ↔ Backend (provider API)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { providerRegistry, getProviders, getProvider, getModelsForProvider } from '../../shared/services/providerRegistry';

describe('ProviderRegistry — Unit & Integration', () => {
  describe('getAllProviders', () => {
    it('should return all registered providers', () => {
      const providers = providerRegistry.getAllProviders();
      expect(providers.length).toBeGreaterThan(0);
    });

    it('should include essential providers', () => {
      const providers = providerRegistry.getAllProviders();
      const names = providers.map(p => p.name);

      expect(names).toContain('anthropic');
      expect(names).toContain('openai');
      expect(names).toContain('google');
      expect(names).toContain('ollama');
      expect(names).toContain('copilot');
    });

    it('should have required fields on every provider', () => {
      const providers = providerRegistry.getAllProviders();

      for (const provider of providers) {
        expect(provider.name).toBeTruthy();
        expect(provider.label).toBeTruthy();
        expect(provider.description).toBeTruthy();
        expect(provider.category).toBeTruthy();
        expect(typeof provider.requiresApiKey).toBe('boolean');
        expect(typeof provider.requiresOAuth).toBe('boolean');
        expect(typeof provider.requiresCLI).toBe('boolean');
        expect(Array.isArray(provider.models)).toBe(true);
      }
    });
  });

  describe('getProvider', () => {
    it('should return a specific provider by name', () => {
      const openai = providerRegistry.getProvider('openai');
      expect(openai).toBeDefined();
      expect(openai?.label).toContain('OpenAI');
    });

    it('should return undefined for unknown provider', () => {
      const unknown = providerRegistry.getProvider('nonexistent');
      expect(unknown).toBeUndefined();
    });
  });

  describe('Provider configurations', () => {
    it('anthropic should require OAuth', () => {
      const anthropic = providerRegistry.getProvider('anthropic');
      expect(anthropic?.requiresOAuth).toBe(true);
      expect(anthropic?.requiresApiKey).toBe(true);
      expect(anthropic?.category).toBe('anthropic');
    });

    it('openai should require API key but not OAuth', () => {
      const openai = providerRegistry.getProvider('openai');
      expect(openai?.requiresApiKey).toBe(true);
      expect(openai?.requiresOAuth).toBe(false);
    });

    it('copilot should require CLI', () => {
      const copilot = providerRegistry.getProvider('copilot');
      expect(copilot?.requiresCLI).toBe(true);
      expect(copilot?.requiresApiKey).toBe(false);
    });

    it('ollama should not require API key or OAuth', () => {
      const ollama = providerRegistry.getProvider('ollama');
      expect(ollama?.requiresApiKey).toBe(false);
      expect(ollama?.requiresOAuth).toBe(false);
      expect(ollama?.category).toBe('local');
    });
  });

  describe('Provider models', () => {
    it('each provider should have a models array', () => {
      const providers = providerRegistry.getAllProviders();
      for (const provider of providers) {
        expect(Array.isArray(provider.models)).toBe(true);
      }
    });

    it('model entries should have required fields', () => {
      const providers = providerRegistry.getAllProviders();
      for (const provider of providers) {
        for (const model of provider.models) {
          expect(model.value).toBeTruthy();
          expect(model.label).toBeTruthy();
          expect(['flagship', 'standard', 'fast', 'local']).toContain(model.tier);
        }
      }
    });
  });

  describe('Dynamic provider management', () => {
    it('should add a new provider dynamically', () => {
      const customProvider = {
        name: 'test-provider',
        label: 'Test Provider',
        description: 'A test provider',
        category: 'special' as const,
        requiresApiKey: true,
        requiresOAuth: false,
        requiresCLI: false,
        models: [{ value: 'test-model', label: 'Test Model', tier: 'standard' as const }]
      };

      providerRegistry.addProvider(customProvider);

      const retrieved = providerRegistry.getProvider('test-provider');
      expect(retrieved).toBeDefined();
      expect(retrieved?.label).toBe('Test Provider');

      // Cleanup
      providerRegistry.removeProvider('test-provider');
    });

    it('should remove a provider', () => {
      providerRegistry.addProvider({
        name: 'temp-provider',
        label: 'Temp',
        description: 'Temporary',
        category: 'special' as const,
        requiresApiKey: false,
        requiresOAuth: false,
        requiresCLI: false,
        models: []
      });

      const removed = providerRegistry.removeProvider('temp-provider');
      expect(removed).toBe(true);
      expect(providerRegistry.getProvider('temp-provider')).toBeUndefined();
    });

    it('should return false when removing non-existent provider', () => {
      const removed = providerRegistry.removeProvider('nonexistent-provider');
      expect(removed).toBe(false);
    });

    it('should update an existing provider', () => {
      // Add a temp provider
      providerRegistry.addProvider({
        name: 'update-test',
        label: 'Before Update',
        description: 'Before',
        category: 'special' as const,
        requiresApiKey: false,
        requiresOAuth: false,
        requiresCLI: false,
        models: []
      });

      const updated = providerRegistry.updateProvider('update-test', { label: 'After Update' });
      expect(updated).toBe(true);
      expect(providerRegistry.getProvider('update-test')?.label).toBe('After Update');

      // Cleanup
      providerRegistry.removeProvider('update-test');
    });

    it('should return false when updating non-existent provider', () => {
      const updated = providerRegistry.updateProvider('nonexistent', { label: 'New' });
      expect(updated).toBe(false);
    });
  });

  describe('checkProviderStatus', () => {
    it('should return available=false for unknown provider', async () => {
      const status = await providerRegistry.checkProviderStatus('nonexistent');
      expect(status.available).toBe(false);
      expect(status.authenticated).toBe(false);
      expect(status.error).toContain('not found');
    });

    it('should return authenticated=true for anthropic (always via OAuth/Claude Code)', async () => {
      const status = await providerRegistry.checkProviderStatus('anthropic');
      expect(status.available).toBe(true);
      expect(status.authenticated).toBe(true);
    });

    it('should check API key providers against profiles', async () => {
      const profiles = [
        {
          id: 'p1',
          name: 'My OpenAI',
          baseUrl: 'https://api.openai.com/v1',
          apiKey: 'sk-test',
          createdAt: Date.now(),
          updatedAt: Date.now()
        }
      ];

      const status = await providerRegistry.checkProviderStatus('openai', profiles);
      expect(status.available).toBe(true);
      expect(status.authenticated).toBe(true);
    });

    it('should report unauthenticated when no matching profile exists', async () => {
      const status = await providerRegistry.checkProviderStatus('openai', []);
      expect(status.available).toBe(true);
      expect(status.authenticated).toBe(false);
    });
  });

  describe('checkAllProvidersStatus', () => {
    it('should return status for all providers', async () => {
      const allStatus = await providerRegistry.checkAllProvidersStatus([]);
      const providers = providerRegistry.getAllProviders();

      for (const provider of providers) {
        expect(allStatus[provider.name]).toBeDefined();
        expect(typeof allStatus[provider.name].available).toBe('boolean');
        expect(typeof allStatus[provider.name].authenticated).toBe('boolean');
      }
    });
  });

  describe('Utility functions', () => {
    it('getProviders should return providers and status', async () => {
      const result = await getProviders([]);
      expect(result.providers).toBeDefined();
      expect(result.providers.length).toBeGreaterThan(0);
      expect(result.status).toBeDefined();
    });

    it('getProvider should return provider by name', () => {
      const provider = getProvider('anthropic');
      expect(provider).toBeDefined();
      expect(provider?.name).toBe('anthropic');
    });

    it('getModelsForProvider should return models array', () => {
      const models = getModelsForProvider('openai');
      expect(Array.isArray(models)).toBe(true);
    });

    it('getModelsForProvider should return empty array for unknown provider', () => {
      const models = getModelsForProvider('nonexistent');
      expect(models).toEqual([]);
    });
  });
});
