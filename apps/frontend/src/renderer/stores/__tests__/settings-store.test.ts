/**
 * @vitest-environment jsdom
 */

/**
 * Unit tests for Settings Store
 * Tests Zustand store for app settings, API profiles, connection testing, and model discovery
 * Improvement 6.1: Add tests for critical Zustand stores (settings-store)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { AppSettings } from '../../../shared/types';
import type { APIProfile, TestConnectionResult, ModelInfo } from '@shared/types/profile';

// Mock toast
vi.mock('../../hooks/use-toast', () => ({
  toast: vi.fn(),
}));

// Mock Sentry
vi.mock('../../lib/sentry', () => ({
  markSettingsLoaded: vi.fn(),
}));

// Mock electronAPI
const mockGetSettings = vi.fn();
const mockSaveSettings = vi.fn();
const mockGetAPIProfiles = vi.fn();
const mockSaveAPIProfile = vi.fn();
const mockUpdateAPIProfile = vi.fn();
const mockDeleteAPIProfile = vi.fn();
const mockSetActiveAPIProfile = vi.fn();
const mockTestConnection = vi.fn();
const mockDiscoverModels = vi.fn();
const mockGetClaudeCodeOnboardingStatus = vi.fn();

vi.stubGlobal('window', {
  electronAPI: {
    getSettings: mockGetSettings,
    saveSettings: mockSaveSettings,
    getAPIProfiles: mockGetAPIProfiles,
    saveAPIProfile: mockSaveAPIProfile,
    updateAPIProfile: mockUpdateAPIProfile,
    deleteAPIProfile: mockDeleteAPIProfile,
    setActiveAPIProfile: mockSetActiveAPIProfile,
    testConnection: mockTestConnection,
    discoverModels: mockDiscoverModels,
    getClaudeCodeOnboardingStatus: mockGetClaudeCodeOnboardingStatus,
  },
});

describe('Settings Store', () => {
  let useSettingsStore: typeof import('../settings-store').useSettingsStore;
  let loadSettings: typeof import('../settings-store').loadSettings;
  let saveSettings: typeof import('../settings-store').saveSettings;
  let loadProfiles: typeof import('../settings-store').loadProfiles;

  beforeEach(async () => {
    vi.clearAllMocks();
    vi.resetModules();

    const storeModule = await import('../settings-store');
    useSettingsStore = storeModule.useSettingsStore;
    loadSettings = storeModule.loadSettings;
    saveSettings = storeModule.saveSettings;
    loadProfiles = storeModule.loadProfiles;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initial State', () => {
    it('should have default initial state', () => {
      const state = useSettingsStore.getState();
      expect(state.settings).toBeDefined();
      expect(state.isLoading).toBe(true); // Starts as true since settings load on init
      expect(state.error).toBeNull();
      expect(state.profiles).toEqual([]);
      expect(state.activeProfileId).toBeNull();
      expect(state.profilesLoading).toBe(false);
      expect(state.profilesError).toBeNull();
      expect(state.isTestingConnection).toBe(false);
      expect(state.testConnectionResult).toBeNull();
      expect(state.modelsLoading).toBe(false);
      expect(state.modelsError).toBeNull();
    });
  });

  describe('setSettings', () => {
    it('should replace settings entirely', () => {
      const newSettings = { theme: 'dark', autoBuildPath: '/test' } as unknown as AppSettings;
      useSettingsStore.getState().setSettings(newSettings);
      expect(useSettingsStore.getState().settings).toEqual(newSettings);
    });
  });

  describe('updateSettings', () => {
    it('should merge updates into existing settings', () => {
      const initialSettings = useSettingsStore.getState().settings;
      useSettingsStore.getState().updateSettings({ autoBuildPath: '/new-path' } as Partial<AppSettings>);

      const updated = useSettingsStore.getState().settings;
      expect(updated.autoBuildPath).toBe('/new-path');
      // Other settings should remain unchanged
      expect(updated).toEqual({ ...initialSettings, autoBuildPath: '/new-path' });
    });

    it('should handle multiple sequential updates', () => {
      useSettingsStore.getState().updateSettings({ autoBuildPath: '/path1' } as Partial<AppSettings>);
      useSettingsStore.getState().updateSettings({ autoBuildPath: '/path2' } as Partial<AppSettings>);
      expect(useSettingsStore.getState().settings.autoBuildPath).toBe('/path2');
    });
  });

  describe('setLoading / setError', () => {
    it('should set loading state', () => {
      useSettingsStore.getState().setLoading(true);
      expect(useSettingsStore.getState().isLoading).toBe(true);

      useSettingsStore.getState().setLoading(false);
      expect(useSettingsStore.getState().isLoading).toBe(false);
    });

    it('should set and clear error', () => {
      useSettingsStore.getState().setError('Something went wrong');
      expect(useSettingsStore.getState().error).toBe('Something went wrong');

      useSettingsStore.getState().setError(null);
      expect(useSettingsStore.getState().error).toBeNull();
    });
  });

  describe('loadSettings (IPC)', () => {
    it('should load settings successfully from IPC', async () => {
      const mockSettings: Partial<AppSettings> = {
        autoBuildPath: '/test',
        onboardingCompleted: true,
      };

      mockGetSettings.mockResolvedValue({ success: true, data: mockSettings });

      await loadSettings();

      const state = useSettingsStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.settings.autoBuildPath).toBe('/test');
    });

    it('should handle IPC failure gracefully', async () => {
      mockGetSettings.mockResolvedValue({ success: false, error: 'Settings file not found' });

      await loadSettings();

      const state = useSettingsStore.getState();
      expect(state.isLoading).toBe(false);
      // No error set for non-success without exception
    });

    it('should handle IPC exception gracefully', async () => {
      mockGetSettings.mockRejectedValue(new Error('IPC communication failed'));

      await loadSettings();

      const state = useSettingsStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe('IPC communication failed');
    });

    it('should set loading true during load and false after', async () => {
      let resolveSettings: (value: unknown) => void = () => {};
      const settingsPromise = new Promise((resolve) => { resolveSettings = resolve; });
      mockGetSettings.mockReturnValue(settingsPromise);

      const loadPromise = loadSettings();
      expect(useSettingsStore.getState().isLoading).toBe(true);

      resolveSettings?.({ success: true, data: { onboardingCompleted: true } });
      await loadPromise;

      expect(useSettingsStore.getState().isLoading).toBe(false);
    });
  });

  describe('saveSettings (IPC)', () => {
    it('should save settings and update store on success', async () => {
      mockSaveSettings.mockResolvedValue({ success: true });

      const result = await saveSettings({ autoBuildPath: '/saved-path' } as Partial<AppSettings>);

      expect(result).toBe(true);
      expect(mockSaveSettings).toHaveBeenCalledWith({ autoBuildPath: '/saved-path' });
      expect(useSettingsStore.getState().settings.autoBuildPath).toBe('/saved-path');
    });

    it('should return false on save failure', async () => {
      mockSaveSettings.mockResolvedValue({ success: false });

      const result = await saveSettings({ autoBuildPath: '/fail' } as Partial<AppSettings>);

      expect(result).toBe(false);
    });

    it('should return false on exception', async () => {
      mockSaveSettings.mockRejectedValue(new Error('Save failed'));

      const result = await saveSettings({ autoBuildPath: '/error' } as Partial<AppSettings>);

      expect(result).toBe(false);
    });
  });

  describe('Profile Management', () => {
    const mockProfile: APIProfile = {
      id: 'profile-1',
      name: 'Test Profile',
      baseUrl: 'https://api.openai.com/v1',
      apiKey: 'sk-test-key',
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    describe('setProfiles', () => {
      it('should set profiles and active profile ID', () => {
        useSettingsStore.getState().setProfiles([mockProfile], 'profile-1');

        const state = useSettingsStore.getState();
        expect(state.profiles).toHaveLength(1);
        expect(state.profiles[0].id).toBe('profile-1');
        expect(state.activeProfileId).toBe('profile-1');
      });

      it('should handle empty profiles', () => {
        useSettingsStore.getState().setProfiles([], null);

        const state = useSettingsStore.getState();
        expect(state.profiles).toEqual([]);
        expect(state.activeProfileId).toBeNull();
      });
    });

    describe('loadProfiles (IPC)', () => {
      it('should load profiles from IPC successfully', async () => {
        mockGetAPIProfiles.mockResolvedValue({
          success: true,
          data: { profiles: [mockProfile], activeProfileId: 'profile-1' },
        });

        await loadProfiles();

        const state = useSettingsStore.getState();
        expect(state.profiles).toHaveLength(1);
        expect(state.activeProfileId).toBe('profile-1');
        expect(state.profilesLoading).toBe(false);
      });

      it('should handle load profiles failure', async () => {
        mockGetAPIProfiles.mockRejectedValue(new Error('Load failed'));

        await loadProfiles();

        const state = useSettingsStore.getState();
        expect(state.profilesError).toBe('Load failed');
        expect(state.profilesLoading).toBe(false);
      });
    });

    describe('saveProfile', () => {
      it('should save a new profile and re-fetch from backend', async () => {
        mockSaveAPIProfile.mockResolvedValue({ success: true, data: mockProfile });
        mockGetAPIProfiles.mockResolvedValue({
          success: true,
          data: { profiles: [mockProfile], activeProfileId: 'profile-1' },
        });

        const result = await useSettingsStore.getState().saveProfile({
          name: 'Test Profile',
          baseUrl: 'https://api.openai.com/v1',
          apiKey: 'sk-test-key',
          model: 'gpt-4',
        } as any);

        expect(result).toBe(true);
        const state = useSettingsStore.getState();
        expect(state.profiles).toHaveLength(1);
        expect(state.activeProfileId).toBe('profile-1');
      });

      it('should handle save profile failure', async () => {
        mockSaveAPIProfile.mockResolvedValue({ success: false, error: 'Duplicate name' });

        const result = await useSettingsStore.getState().saveProfile({
          name: 'Test Profile',
        } as any);

        expect(result).toBe(false);
        expect(useSettingsStore.getState().profilesError).toBe('Duplicate name');
      });
    });

    describe('updateProfile', () => {
      it('should update existing profile', async () => {
        useSettingsStore.setState({ profiles: [mockProfile] });
        const updatedProfile = { ...mockProfile, name: 'Updated Profile' };

        mockUpdateAPIProfile.mockResolvedValue({ success: true, data: updatedProfile });

        const result = await useSettingsStore.getState().updateProfile(updatedProfile);

        expect(result).toBe(true);
        expect(useSettingsStore.getState().profiles[0].name).toBe('Updated Profile');
      });

      it('should handle update failure', async () => {
        useSettingsStore.setState({ profiles: [mockProfile] });
        mockUpdateAPIProfile.mockResolvedValue({ success: false, error: 'Not found' });

        const result = await useSettingsStore.getState().updateProfile(mockProfile);

        expect(result).toBe(false);
        expect(useSettingsStore.getState().profilesError).toBe('Not found');
      });
    });

    describe('deleteProfile', () => {
      it('should delete profile and clear activeProfileId if needed', async () => {
        useSettingsStore.setState({ profiles: [mockProfile], activeProfileId: 'profile-1' });
        mockDeleteAPIProfile.mockResolvedValue({ success: true });

        const result = await useSettingsStore.getState().deleteProfile('profile-1');

        expect(result).toBe(true);
        const state = useSettingsStore.getState();
        expect(state.profiles).toHaveLength(0);
        expect(state.activeProfileId).toBeNull();
      });

      it('should not clear activeProfileId when deleting a non-active profile', async () => {
        const profile2: APIProfile = { ...mockProfile, id: 'profile-2', name: 'Profile 2' };
        useSettingsStore.setState({
          profiles: [mockProfile, profile2],
          activeProfileId: 'profile-1',
        });
        mockDeleteAPIProfile.mockResolvedValue({ success: true });

        await useSettingsStore.getState().deleteProfile('profile-2');

        expect(useSettingsStore.getState().activeProfileId).toBe('profile-1');
        expect(useSettingsStore.getState().profiles).toHaveLength(1);
      });

      it('should handle delete failure', async () => {
        useSettingsStore.setState({ profiles: [mockProfile] });
        mockDeleteAPIProfile.mockResolvedValue({ success: false, error: 'Permission denied' });

        const result = await useSettingsStore.getState().deleteProfile('profile-1');

        expect(result).toBe(false);
        expect(useSettingsStore.getState().profiles).toHaveLength(1);
      });
    });

    describe('setActiveProfile', () => {
      it('should set active profile', async () => {
        mockSetActiveAPIProfile.mockResolvedValue({ success: true });

        const result = await useSettingsStore.getState().setActiveProfile('profile-1');

        expect(result).toBe(true);
        expect(useSettingsStore.getState().activeProfileId).toBe('profile-1');
      });

      it('should clear active profile with null', async () => {
        useSettingsStore.setState({ activeProfileId: 'profile-1' });
        mockSetActiveAPIProfile.mockResolvedValue({ success: true });

        const result = await useSettingsStore.getState().setActiveProfile(null);

        expect(result).toBe(true);
        expect(useSettingsStore.getState().activeProfileId).toBeNull();
      });

      it('should handle set active profile failure', async () => {
        mockSetActiveAPIProfile.mockResolvedValue({ success: false, error: 'Profile not found' });

        const result = await useSettingsStore.getState().setActiveProfile('nonexistent');

        expect(result).toBe(false);
        expect(useSettingsStore.getState().profilesError).toBe('Profile not found');
      });
    });
  });

  describe('Test Connection', () => {
    it('should test connection successfully', async () => {
      const successResult: TestConnectionResult = {
        success: true,
        message: 'Connection OK',
      };
      mockTestConnection.mockResolvedValue({ success: true, data: successResult });

      const result = await useSettingsStore.getState().testConnection('https://api.test.com', 'key-123');

      expect(result).toEqual(successResult);
      const state = useSettingsStore.getState();
      expect(state.isTestingConnection).toBe(false);
      expect(state.testConnectionResult).toEqual(successResult);
    });

    it('should handle connection test failure from IPC', async () => {
      mockTestConnection.mockResolvedValue({ success: false, error: 'Invalid API key' });

      const result = await useSettingsStore.getState().testConnection('https://api.test.com', 'bad-key');

      expect(result).toBeDefined();
      expect(result?.success).toBe(false);
      expect(result?.message).toBe('Invalid API key');
      expect(useSettingsStore.getState().isTestingConnection).toBe(false);
    });

    it('should handle connection test exception', async () => {
      mockTestConnection.mockRejectedValue(new Error('Network error'));

      const result = await useSettingsStore.getState().testConnection('https://api.test.com', 'key');

      expect(result).toBeDefined();
      expect(result?.success).toBe(false);
      expect(result?.message).toBe('Network error');
    });

    it('should set isTestingConnection during test', async () => {
      let resolveTest: (value: unknown) => void = () => {};
      const testPromise = new Promise((resolve) => { resolveTest = resolve; });
      mockTestConnection.mockReturnValue(testPromise);

      const testCall = useSettingsStore.getState().testConnection('https://api.test.com', 'key');
      expect(useSettingsStore.getState().isTestingConnection).toBe(true);

      resolveTest?.({ success: true, data: { success: true, message: 'OK' } });
      await testCall;

      expect(useSettingsStore.getState().isTestingConnection).toBe(false);
    });
  });

  describe('Model Discovery', () => {
    const mockModels: ModelInfo[] = [
      { id: 'gpt-4', display_name: 'GPT-4' },
      { id: 'gpt-3.5-turbo', display_name: 'GPT-3.5 Turbo' },
    ];

    it('should discover models successfully', async () => {
      mockDiscoverModels.mockResolvedValue({ success: true, data: { models: mockModels } });

      const result = await useSettingsStore.getState().discoverModels('https://api.openai.com', 'sk-key');

      expect(result).toEqual(mockModels);
      expect(useSettingsStore.getState().modelsLoading).toBe(false);
    });

    it('should cache discovered models', async () => {
      mockDiscoverModels.mockResolvedValue({ success: true, data: { models: mockModels } });

      // First call
      await useSettingsStore.getState().discoverModels('https://api.openai.com', 'sk-test-key');
      // Second call with same params should use cache
      const result = await useSettingsStore.getState().discoverModels('https://api.openai.com', 'sk-test-key');

      expect(result).toEqual(mockModels);
      // Should only call IPC once (second call uses cache)
      expect(mockDiscoverModels).toHaveBeenCalledTimes(1);
    });

    it('should not cache across different API keys', async () => {
      mockDiscoverModels.mockResolvedValue({ success: true, data: { models: mockModels } });

      await useSettingsStore.getState().discoverModels('https://api.openai.com', 'sk-key1');
      await useSettingsStore.getState().discoverModels('https://api.openai.com', 'sk-key2');

      expect(mockDiscoverModels).toHaveBeenCalledTimes(2);
    });

    it('should handle discovery failure', async () => {
      mockDiscoverModels.mockResolvedValue({ success: false, error: 'Unauthorized' });

      const result = await useSettingsStore.getState().discoverModels('https://api.openai.com', 'bad-key');

      expect(result).toBeNull();
      expect(useSettingsStore.getState().modelsError).toBe('Unauthorized');
    });

    it('should handle discovery exception', async () => {
      mockDiscoverModels.mockRejectedValue(new Error('Network error'));

      const result = await useSettingsStore.getState().discoverModels('https://api.openai.com', 'key');

      expect(result).toBeNull();
      expect(useSettingsStore.getState().modelsError).toBe('Network error');
    });
  });

  describe('setProviderPriorityOrder', () => {
    it('should update provider priority order in settings', () => {
      const order = ['anthropic', 'openai', 'google'] as any[];
      useSettingsStore.getState().setProviderPriorityOrder(order);

      expect(useSettingsStore.getState().settings.providerPriorityOrder).toEqual(order);
    });

    it('should persist to main process via IPC', () => {
      const order = ['openai'] as any[];
      useSettingsStore.getState().setProviderPriorityOrder(order);

      expect(mockSaveSettings).toHaveBeenCalledWith({ providerPriorityOrder: order });
    });
  });
});
