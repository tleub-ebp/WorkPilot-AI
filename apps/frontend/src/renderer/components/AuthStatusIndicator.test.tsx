/**
 * @vitest-environment jsdom
 */
/**
 * Tests for AuthStatusIndicator component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { AuthStatusIndicator } from './AuthStatusIndicator';
import { ProviderContextProvider } from './ProviderContext';
import { useSettingsStore } from '../stores/settings-store';
import type { APIProfile } from '../../shared/types/profile';
import type { ReactNode } from 'react';

/** Wraps component in required context providers */
function renderWithProviders(ui: ReactNode) {
  return render(<ProviderContextProvider>{ui}</ProviderContextProvider>);
}

// Mock the settings store
vi.mock('../stores/settings-store', () => ({
  useSettingsStore: vi.fn()
}));

// Mock i18n translation function
vi.mock('react-i18next', () => ({
  useTranslation: vi.fn(() => ({
    t: (key: string, params?: Record<string, unknown>) => {
      // For translation keys, return values for testing
      const translations: Record<string, string> = {
        'common:usage.authentication': 'Authentication',
        'common:usage.oauth': 'OAuth',
        'common:usage.apiProfile': 'API Profile',
        'common:usage.provider': 'Provider',
        'common:usage.providerAnthropic': 'Anthropic',
        'common:usage.providerOpenAI': 'OpenAI',
        'common:usage.providerOllama': 'Ollama',
        'common:usage.providerOllamaLocal': 'Ollama (Local)',
        'common:usage.authenticationAriaLabel': 'Authentication: {{provider}}',
        'common:usage.profile': 'Profile',
        'common:usage.id': 'ID',
        'common:usage.apiEndpoint': 'API Endpoint',
        'common:usage.claudeCode': 'Claude Code',
        'common:usage.apiKey': 'API Key'
      };
      // Handle interpolation (e.g., "Authentication: {{provider}}")
      if (params && Object.keys(params).length > 0) {
        const translated = translations[key] || key;
        if (translated.includes('{{provider}}')) {
          return translated.replace('{{provider}}', String(params.provider));
        }
        return translated;
      }
      return translations[key] || key;
    }
  }))
}));

/**
 * Creates a mock settings store with optional overrides
 * @param overrides - Partial store state to override defaults
 * @returns Complete mock settings store object
 */
function createUseSettingsStoreMock(overrides?: Partial<ReturnType<typeof useSettingsStore>>) {
  return {
    profiles: testProfiles,
    activeProfileId: null,
    deleteProfile: vi.fn().mockResolvedValue(true),
    setActiveProfile: vi.fn().mockResolvedValue(true),
    profilesLoading: false,
    settings: {} as any,
    isLoading: false,
    error: null,
    setSettings: vi.fn(),
    updateSettings: vi.fn(),
    setLoading: vi.fn(),
    setError: vi.fn(),
    setProfiles: vi.fn(),
    setProfilesLoading: vi.fn(),
    setProfilesError: vi.fn(),
    saveProfile: vi.fn().mockResolvedValue(true),
    updateProfile: vi.fn().mockResolvedValue(true),
    profilesError: null,
    ...overrides
  };
}

// Test profile data
const testProfiles: APIProfile[] = [
  {
    id: 'profile-1',
    name: 'Production API',
    baseUrl: 'https://api.anthropic.com',
    apiKey: 'sk-ant-prod-key-1234',
    models: { default: 'claude-sonnet-4-5-20250929' },
    createdAt: Date.now(),
    updatedAt: Date.now()
  },
  {
    id: 'profile-2',
    name: 'Development API',
    baseUrl: 'https://dev-api.example.com/v1',
    apiKey: 'sk-ant-test-key-5678',
    models: undefined,
    createdAt: Date.now(),
    updatedAt: Date.now()
  },
  {
    id: 'profile-3',
    name: 'Ollama Remote',
    baseUrl: 'https://ollama.ai/api',
    apiKey: 'sk-ollama-key-1234',
    models: undefined,
    createdAt: Date.now(),
    updatedAt: Date.now()
  },
  {
    id: 'profile-4',
    name: 'Ollama Local',
    baseUrl: 'http://localhost:11434/v1',
    apiKey: 'ollama-local-key-5678',
    models: undefined,
    createdAt: Date.now(),
    updatedAt: Date.now()
  }
];

describe('AuthStatusIndicator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.electronAPI usage functions
    (window as any).electronAPI = {
      onUsageUpdated: vi.fn(() => vi.fn()), // Returns unsubscribe function
      requestUsageUpdate: vi.fn().mockResolvedValue({ success: false, data: null })
    };
  });

  describe('when using OAuth (no active profile)', () => {
    beforeEach(() => {
      vi.mocked(useSettingsStore).mockReturnValue(
        createUseSettingsStoreMock({ activeProfileId: null })
      );
    });

    it('should display Anthropic badge with Lock icon for OAuth', () => {
      renderWithProviders(<AuthStatusIndicator />);

      expect(screen.getByText('Anthropic')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /authentication: anthropic/i })).toBeInTheDocument();
    });

    it('should have correct aria-label for OAuth', () => {
      renderWithProviders(<AuthStatusIndicator />);

      expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Authentication: Anthropic');
    });
  });

  describe('when using API profile', () => {
    beforeEach(() => {
      vi.mocked(useSettingsStore).mockReturnValue(
        createUseSettingsStoreMock({ activeProfileId: 'profile-1' })
      );
    });

    it('should display provider name badge with Key icon for API profile', () => {
      renderWithProviders(<AuthStatusIndicator />);

      // Badge shows the provider name detected from baseUrl, not "API Key"
      expect(screen.getByText('Anthropic')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /authentication: anthropic/i })).toBeInTheDocument();
    });

    it('should have correct aria-label for profile', () => {
      renderWithProviders(<AuthStatusIndicator />);

      expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Authentication: Anthropic');
    });
  });

  describe('when active profile ID references non-existent profile', () => {
    beforeEach(() => {
      vi.mocked(useSettingsStore).mockReturnValue(
        createUseSettingsStoreMock({ activeProfileId: 'non-existent-id' })
      );
    });

    it('should fallback to OAuth (Anthropic) when profile not found', () => {
      renderWithProviders(<AuthStatusIndicator />);

      // Falls back to Anthropic provider label
      expect(screen.getByText('Anthropic')).toBeInTheDocument();
    });
  });

  describe('provider detection for different API profiles', () => {
    it('should display Ollama badge for Ollama profile', () => {
      vi.mocked(useSettingsStore).mockReturnValue(
        createUseSettingsStoreMock({ activeProfileId: 'profile-3' })
      );

      renderWithProviders(<AuthStatusIndicator />);

      expect(screen.getByText('Ollama')).toBeInTheDocument();
      expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Authentication: Ollama');
    });

    it('should display Ollama (Local) badge for Ollama Local profile', () => {
      vi.mocked(useSettingsStore).mockReturnValue(
        createUseSettingsStoreMock({ activeProfileId: 'profile-4' })
      );

      renderWithProviders(<AuthStatusIndicator />);

      expect(screen.getByText('Ollama (Local)')).toBeInTheDocument();
      expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Authentication: Ollama (Local)');
    });

    it('should apply correct color classes for each provider', () => {
      // Test Anthropic (orange)
      vi.mocked(useSettingsStore).mockReturnValue(
        createUseSettingsStoreMock({ activeProfileId: 'profile-1' })
      );

      const { rerender } = renderWithProviders(<AuthStatusIndicator />);
      const anthropicButton = screen.getByRole('button');
      expect(anthropicButton.className).toContain('text-orange-500');

      // Test Ollama (emerald)
      vi.mocked(useSettingsStore).mockReturnValue(
        createUseSettingsStoreMock({ activeProfileId: 'profile-3' })
      );

      rerender(<ProviderContextProvider><AuthStatusIndicator /></ProviderContextProvider>);
      const ollamaButton = screen.getByRole('button');
      expect(ollamaButton.className).toContain('text-emerald-500');

      // Test Ollama Local (teal)
      vi.mocked(useSettingsStore).mockReturnValue(
        createUseSettingsStoreMock({ activeProfileId: 'profile-4' })
      );

      rerender(<ProviderContextProvider><AuthStatusIndicator /></ProviderContextProvider>);
      const ollamaLocalButton = screen.getByRole('button');
      expect(ollamaLocalButton.className).toContain('text-teal-500');
    });
  });

  describe('component structure', () => {
    beforeEach(() => {
      vi.mocked(useSettingsStore).mockReturnValue(
        createUseSettingsStoreMock()
      );
    });

    it('should be a valid React component', () => {
      expect(() => renderWithProviders(<AuthStatusIndicator />)).not.toThrow();
    });
  });
});
