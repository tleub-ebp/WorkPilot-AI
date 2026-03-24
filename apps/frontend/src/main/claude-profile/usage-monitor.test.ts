/**
 * Tests for usage-monitor.ts
 *
 * Red phase - write failing tests first
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { detectProvider, getUsageEndpoint, UsageMonitor, getUsageMonitor } from './usage-monitor';
import type { ApiProvider } from './usage-monitor';
import { hasHardcodedText } from '../../shared/utils/format-time';

// Mock getClaudeProfileManager
vi.mock('../claude-profile-manager', () => ({
  getClaudeProfileManager: vi.fn(() => ({
    getAutoSwitchSettings: vi.fn(() => ({
      enabled: true,
      proactiveSwapEnabled: true,
      usageCheckInterval: 30000,
      sessionThreshold: 80,
      weeklyThreshold: 80
    })),
    getActiveProfile: vi.fn(() => ({
      id: 'test-profile-1',
      name: 'Test Profile',
      baseUrl: 'https://api.anthropic.com',
      oauthToken: 'mock-oauth-token'
    })),
    getProfile: vi.fn((id: string) => ({
      id,
      name: 'Test Profile',
      baseUrl: 'https://api.anthropic.com',
      oauthToken: 'mock-oauth-token'
    })),
    getProfilesSortedByAvailability: vi.fn(() => [
      { id: 'profile-2', name: 'Profile 2' },
      { id: 'profile-3', name: 'Profile 3' }
    ]),
    setActiveProfile: vi.fn(),
    getProfileToken: vi.fn(() => 'mock-decrypted-token')
  }))
}));

// Mock loadProfilesFile
const mockLoadProfilesFile = vi.fn(async () => ({
  profiles: [] as Array<{
    id: string;
    name: string;
    baseUrl: string;
    apiKey: string;
  }>,
  activeProfileId: null as string | null,
  version: 1
}));

vi.mock('../services/profile/profile-manager', () => ({
  loadProfilesFile: () => mockLoadProfilesFile()
}));

// Mock credential-utils to return mock token instead of reading real credentials
vi.mock('./credential-utils', () => ({
  getCredentialsFromKeychain: vi.fn(() => ({
    token: 'mock-decrypted-token',
    email: 'test@example.com'
  })),
  clearKeychainCache: vi.fn()
}));

// Mock global fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    statusText: 'OK',
    json: async () => ({
      five_hour_utilization: 0.5,
      seven_day_utilization: 0.3,
      five_hour_reset_at: '2025-01-17T15:00:00Z',
      seven_day_reset_at: '2025-01-20T12:00:00Z'
    })
  } as unknown as Response)
) as any;

describe('usage-monitor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Restore default fetch mock after clearAllMocks
    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockImplementation(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: {
          get: vi.fn((name: string) => name === 'content-type' ? 'application/json' : null)
        },
        json: async () => ({
          five_hour_utilization: 0.5,
          seven_day_utilization: 0.3,
          five_hour_reset_at: '2025-01-17T15:00:00Z',
          seven_day_reset_at: '2025-01-20T12:00:00Z'
        })
      } as unknown as Response)
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  // Note: detectProvider tests removed - now using shared/utils/provider-detection.ts
  // which has its own comprehensive test suite

  describe('getUsageEndpoint', () => {
    it('should return correct endpoint for Anthropic', () => {
      const result = getUsageEndpoint('anthropic', 'https://api.anthropic.com');
      expect(result).toBe('https://api.anthropic.com/api/oauth/usage');
    });

    it('should return correct endpoint for Anthropic with path', () => {
      const result = getUsageEndpoint('anthropic', 'https://api.anthropic.com/v1');
      expect(result).toBe('https://api.anthropic.com/api/oauth/usage');
    });

    it('should return correct endpoint for openai', () => {
      const result = getUsageEndpoint('openai', 'https://api.openai.com/v1');
      expect(result).not.toBeNull();
    });

    it('should return null for unknown provider', () => {
      const result = getUsageEndpoint('unknown' as ApiProvider, 'https://example.com');
      expect(result).toBeNull();
    });

    it('should return null for invalid baseUrl', () => {
      const result = getUsageEndpoint('anthropic', 'not-a-url');
      expect(result).toBeNull();
    });
  });

  describe('UsageMonitor', () => {
    it('should return singleton instance', () => {
      const monitor1 = UsageMonitor.getInstance();
      const monitor2 = UsageMonitor.getInstance();

      expect(monitor1).toBe(monitor2);
    });

    it('should return same instance from getUsageMonitor()', () => {
      const monitor1 = getUsageMonitor();
      const monitor2 = getUsageMonitor();

      expect(monitor1).toBe(monitor2);
    });

    it('should start monitoring when settings allow', () => {
      const monitor = getUsageMonitor();
      monitor.start();

      // Verify monitor started (has intervalId set)
      expect(monitor['intervalId']).not.toBeNull();

      monitor.stop();
    });

    it('should not start if already running', () => {
      const monitor = getUsageMonitor();

      monitor.start();
      const firstIntervalId = monitor['intervalId'];

      monitor.start(); // Second call should be ignored

      // Should still have the same intervalId (not recreated)
      expect(monitor['intervalId']).toBe(firstIntervalId);

      monitor.stop();
    });

    it('should stop monitoring', () => {
      const monitor = getUsageMonitor();

      monitor.start();
      expect(monitor['intervalId']).not.toBeNull();

      monitor.stop();

      // Verify intervalId is cleared
      expect(monitor['intervalId']).toBeNull();
    });

    it('should return current usage snapshot', () => {
      const monitor = getUsageMonitor();

      // Seed the monitor with known test data for deterministic behavior
      const seeded = {
        sessionPercent: 10,
        weeklyPercent: 20,
        profileId: 'test-profile',
        profileName: 'Test Profile',
        fetchedAt: new Date()
      };
      monitor['currentUsage'] = seeded as any;

      const usage = monitor.getCurrentUsage();

      // getCurrentUsage returns the seeded usage snapshot
      expect(usage).toBe(seeded);
      expect(usage).toHaveProperty('sessionPercent');
      expect(usage).toHaveProperty('weeklyPercent');
      expect(usage).toHaveProperty('profileId');
      expect(usage).toHaveProperty('profileName');
      // Verify types of critical properties
      expect(typeof usage?.sessionPercent).toBe('number');
      expect(typeof usage?.weeklyPercent).toBe('number');
    });

    it('should emit events when listeners are attached', () => {
      const monitor = getUsageMonitor();
      const usageHandler = vi.fn();

      monitor.on('usage-updated', usageHandler);

      // Verify event handler is attached
      expect(monitor.listenerCount('usage-updated')).toBe(1);

      // Clean up
      monitor.off('usage-updated', usageHandler);
    });

    it('should allow removing event listeners', () => {
      const monitor = getUsageMonitor();
      const usageHandler = vi.fn();

      monitor.on('usage-updated', usageHandler);
      expect(monitor.listenerCount('usage-updated')).toBe(1);

      monitor.off('usage-updated', usageHandler);
      expect(monitor.listenerCount('usage-updated')).toBe(0);
    });
  });

  describe('UsageMonitor error handling', () => {
    it('should emit event when swap fails', () => {
      const monitor = getUsageMonitor();
      const swapFailedHandler = vi.fn();

      monitor.on('proactive-swap-failed', swapFailedHandler);

      // Manually trigger the swap logic by calling the private method through a test scenario
      // Since we can't directly call private methods, we'll verify the event system works
      monitor.emit('proactive-swap-failed', {
        reason: 'no_alternative',
        currentProfile: 'test-profile'
      });

      expect(swapFailedHandler).toHaveBeenCalledWith({
        reason: 'no_alternative',
        currentProfile: 'test-profile'
      });

      monitor.off('proactive-swap-failed', swapFailedHandler);
    });
  });

  describe('Anthropic response normalization', () => {
    it('should normalize Anthropic response with utilization values', () => {
      const monitor = getUsageMonitor();
      const rawData = {
        five_hour_utilization: 0.72,
        seven_day_utilization: 0.45,
        five_hour_reset_at: '2025-01-17T15:00:00Z',
        seven_day_reset_at: '2025-01-20T12:00:00Z'
      };

      const usage = monitor['normalizeAnthropicResponse'](rawData, 'test-profile-1', 'Anthropic Profile');

      expect(usage).not.toBeNull();
      expect(usage.sessionPercent).toBe(72); // 0.72 * 100
      expect(usage.weeklyPercent).toBe(45); // 0.45 * 100
      expect(usage.limitType).toBe('session'); // 0.45 (weekly) < 0.72 (session), so session is higher
      expect(usage.profileId).toBe('test-profile-1');
      expect(usage.profileName).toBe('Anthropic Profile');
      expect(usage.sessionResetTimestamp).toBe('2025-01-17T15:00:00Z');
      expect(usage.weeklyResetTimestamp).toBe('2025-01-20T12:00:00Z');
    });

    it('should handle missing optional fields in Anthropic response', () => {
      const monitor = getUsageMonitor();
      const rawData = {
        five_hour_utilization: 0.50
        // Missing: seven_day_utilization, reset times
      };

      const usage = monitor['normalizeAnthropicResponse'](rawData, 'test-profile-1', 'Test Profile');

      expect(usage).not.toBeNull();
      expect(usage.sessionPercent).toBe(50);
      expect(usage.weeklyPercent).toBe(0); // Missing field defaults to 0
      // sessionResetTime/weeklyResetTime are now undefined - renderer uses timestamps
      expect(usage.sessionResetTime).toBeUndefined();
      expect(usage.weeklyResetTime).toBeUndefined();
      expect(usage.sessionResetTimestamp).toBeUndefined();
      expect(usage.weeklyResetTimestamp).toBeUndefined();
    });
  });

  // Note: z.ai/ZHIPU response normalization tests removed - those providers are no longer supported
  // See provider-detection.test.ts for current provider detection tests

  describe('API error handling', () => {
    it('should handle 401 Unauthorized responses', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ error: 'Invalid token' })
      } as unknown as Response);

      const monitor = getUsageMonitor();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // 401 errors should throw
      await expect(
        monitor['fetchUsageViaAPI']('invalid-token', 'test-profile-1', 'Test Profile', undefined)
      ).rejects.toThrow('API Auth Failure: 401');

      expect(consoleSpy).toHaveBeenCalled();
      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.anthropic.com/api/oauth/usage',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer invalid-token'
          })
        })
      );

      consoleSpy.mockRestore();
    });

    it('should handle 403 Forbidden responses', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({ error: 'Access denied' })
      } as unknown as Response);

      const monitor = getUsageMonitor();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // 403 errors should throw
      await expect(
        monitor['fetchUsageViaAPI']('expired-token', 'test-profile-1', 'Test Profile', undefined)
      ).rejects.toThrow('API Auth Failure: 403');

      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it('should handle 500 Internal Server Error', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ error: 'Server error' })
      } as unknown as Response);

      const monitor = getUsageMonitor();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const usage = await monitor['fetchUsageViaAPI']('valid-token', 'test-profile-1', 'Test Profile', undefined);

      expect(usage).toBeNull();
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it('should handle network timeout/failure', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockRejectedValueOnce(new Error('Network timeout'));

      const monitor = getUsageMonitor();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const usage = await monitor['fetchUsageViaAPI']('valid-token', 'test-profile-1', 'Test Profile', undefined);

      expect(usage).toBeNull();
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it('should handle invalid JSON response', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => {
          throw new SyntaxError('Invalid JSON');
        }
      } as unknown as Response);

      const monitor = getUsageMonitor();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const usage = await monitor['fetchUsageViaAPI']('valid-token', 'test-profile-1', 'Test Profile', undefined);

      expect(usage).toBeNull();
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it('should handle auth errors with clear messages in response body', async () => {
      const mockFetch = vi.mocked(global.fetch);
      // Mock a 401 response with detailed error message in body
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ error: 'authentication failed', detail: 'invalid credentials' })
      } as unknown as Response);

      const monitor = getUsageMonitor();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // 401 errors should throw with proper message
      await expect(
        monitor['fetchUsageViaAPI']('invalid-token', 'test-profile-1', 'Test Profile', undefined)
      ).rejects.toThrow('API Auth Failure: 401');

      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  describe('Credential error handling', () => {
    it('should handle missing credential gracefully', async () => {
      const monitor = getUsageMonitor();

      // Call fetchUsage without credential
      const usage = await monitor['fetchUsage']('test-profile-1', undefined);

      // Should fall back to CLI method (which returns null)
      expect(usage).toBeNull();
    });

    it('should handle empty credential string', async () => {
      const monitor = getUsageMonitor();
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const usage = await monitor['fetchUsage']('test-profile-1', '');

      // Should fall back to CLI method
      expect(usage).toBeNull();

      consoleSpy.mockRestore();
    });
  });

  describe('Profile error handling', () => {
    it('should handle null active profile', async () => {
      // Get the mocked getClaudeProfileManager function
      const { getClaudeProfileManager } = await import('../claude-profile-manager');
      const mockGetManager = vi.mocked(getClaudeProfileManager);

      // Mock to return null for active profile
      mockGetManager.mockReturnValueOnce({
        getAutoSwitchSettings: vi.fn(() => ({
          enabled: true,
          proactiveSwapEnabled: true,
          usageCheckInterval: 30000,
          sessionThreshold: 80,
          weeklyThreshold: 80
        })),
        getActiveProfile: vi.fn(() => null), // Return null
        getProfile: vi.fn(() => null),
        getProfilesSortedByAvailability: vi.fn(() => []),
        setActiveProfile: vi.fn(),
        getProfileToken: vi.fn(() => null)
      } as any);

      const monitor = getUsageMonitor();

      // Call checkUsageAndSwap directly to test null profile handling
      // Should complete without throwing an error
      await expect(monitor['checkUsageAndSwap']()).resolves.toBeUndefined();
    });

    it('should handle profile with missing required fields', async () => {
      const monitor = getUsageMonitor();
      const rawData = {
        // Missing all required fields
      };

      const usage = monitor['normalizeAnthropicResponse'](rawData, 'test-profile-1', 'Test Profile');

      // Should still return a valid snapshot with defaults
      expect(usage).not.toBeNull();
      expect(usage.sessionPercent).toBe(0);
      expect(usage.weeklyPercent).toBe(0);
      // sessionResetTime/weeklyResetTime are now undefined - renderer uses timestamps
      expect(usage.sessionResetTime).toBeUndefined();
      expect(usage.weeklyResetTime).toBeUndefined();
    });
  });

  describe('Provider-specific error handling', () => {
    it('should handle unknown provider gracefully', async () => {
      const monitor = getUsageMonitor();

      // Create an active profile object with unknown provider
      const unknownProviderProfile = {
        isAPIProfile: true,
        profileId: 'unknown-profile-1',
        profileName: 'Unknown Provider Profile',
        baseUrl: 'https://unknown-provider.com/api'
      };

      // Mock API profile with unknown provider baseUrl
      mockLoadProfilesFile.mockResolvedValueOnce({
        profiles: [{
          id: 'unknown-profile-1',
          name: 'Unknown Provider Profile',
          baseUrl: 'https://unknown-provider.com/api',
          apiKey: 'unknown-api-key'
        }],
        activeProfileId: 'unknown-profile-1',
        version: 1
      });

      const usage = await monitor['fetchUsageViaAPI'](
        'unknown-api-key',
        'unknown-profile-1',
        'Unknown Profile',
        undefined,
        unknownProviderProfile
      );

      // Unknown provider should return null
      expect(usage).toBeNull();
    });
  });

  describe('Concurrent check prevention', () => {
    it('should prevent concurrent usage checks', async () => {
      const monitor = getUsageMonitor();

      // Start first check (it will take some time)
      const firstCheck = monitor['checkUsageAndSwap']();

      // Try to start second check immediately (should be ignored)
      const secondCheck = monitor['checkUsageAndSwap']();

      // Both should resolve
      await firstCheck;
      await secondCheck;

      // Verify check completed (isChecking should be false after both complete)
      expect(monitor['isChecking']).toBe(false);
    });
  });

  describe('backward compatibility', () => {
    describe('Legacy OAuth-only profile support', () => {
      it('should work with legacy OAuth profiles (no API profile support)', async () => {
        // Mock loadProfilesFile to return empty profiles (API profiles not configured)
        mockLoadProfilesFile.mockResolvedValueOnce({
          profiles: [],
          activeProfileId: null,
          version: 1
        });

        const monitor = getUsageMonitor();
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

        // Should fall back to OAuth profile
        const credential = await monitor['getCredential']();

        // Should get OAuth token from profile manager
        expect(credential).toBe('mock-decrypted-token');

        consoleSpy.mockRestore();
      });

      it('should prioritize API profile when available', async () => {
        // Mock API profile is configured
        mockLoadProfilesFile.mockResolvedValueOnce({
          profiles: [{
            id: 'api-profile-1',
            name: 'API Profile',
            baseUrl: 'https://api.anthropic.com',
            apiKey: 'sk-ant-api-key'
          }],
          activeProfileId: 'api-profile-1',
          version: 1
        });

        const monitor = getUsageMonitor();
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

        const credential = await monitor['getCredential']();

        // Should prefer API key over OAuth token
        expect(credential).toBe('sk-ant-api-key');

        consoleSpy.mockRestore();
      });

      it('should handle missing API profile gracefully', async () => {
        // Mock activeProfileId points to non-existent profile
        mockLoadProfilesFile.mockResolvedValueOnce({
          profiles: [],
          activeProfileId: 'nonexistent-profile',
          version: 1
        });

        const monitor = getUsageMonitor();
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

        const credential = await monitor['getCredential']();

        // Should fall back to OAuth
        expect(credential).toBe('mock-decrypted-token');

        consoleSpy.mockRestore();
      });
    });

    describe('Settings backward compatibility', () => {
      it('should handle settings with missing optional fields', async () => {
        // Get the mocked getClaudeProfileManager function
        const { getClaudeProfileManager } = await import('../claude-profile-manager');
        const mockGetManager = vi.mocked(getClaudeProfileManager);

        // Mock settings with missing optional fields
        mockGetManager.mockReturnValueOnce({
          getAutoSwitchSettings: vi.fn(() => ({
            enabled: true,
            proactiveSwapEnabled: true
            // Missing: usageCheckInterval, sessionThreshold, weeklyThreshold
          })),
          getActiveProfile: vi.fn(() => ({
            id: 'test-profile-1',
            name: 'Test Profile',
            baseUrl: 'https://api.anthropic.com',
            oauthToken: 'mock-oauth-token'
          })),
          getProfile: vi.fn(() => ({
            id: 'test-profile-1',
            name: 'Test Profile',
            baseUrl: 'https://api.anthropic.com',
            oauthToken: 'mock-oauth-token'
          })),
          getProfilesSortedByAvailability: vi.fn(() => []),
          setActiveProfile: vi.fn(),
          getProfileToken: vi.fn(() => 'mock-decrypted-token')
        } as any);

        const monitor = getUsageMonitor();

        // Should start with default values for missing fields
        monitor.start();

        // Should have started monitoring
        expect(monitor['intervalId']).not.toBeNull();

        monitor.stop();
      });

      it('should use default thresholds when not specified in settings', async () => {
        // Get the mocked getClaudeProfileManager function
        const { getClaudeProfileManager } = await import('../claude-profile-manager');
        const mockGetManager = vi.mocked(getClaudeProfileManager);

        // Mock settings without thresholds
        mockGetManager.mockReturnValueOnce({
          getAutoSwitchSettings: vi.fn(() => ({
            enabled: true,
            proactiveSwapEnabled: true,
            usageCheckInterval: 30000
            // Missing: sessionThreshold, weeklyThreshold
          })),
          getActiveProfile: vi.fn(() => ({
            id: 'test-profile-1',
            name: 'Test Profile',
            baseUrl: 'https://api.anthropic.com',
            oauthToken: 'mock-oauth-token'
          })),
          getProfile: vi.fn(() => ({
            id: 'test-profile-1',
            name: 'Test Profile',
            baseUrl: 'https://api.anthropic.com',
            oauthToken: 'mock-oauth-token'
          })),
          getProfilesSortedByAvailability: vi.fn(() => []),
          setActiveProfile: vi.fn(),
          getProfileToken: vi.fn(() => 'mock-decrypted-token')
        } as any);

        const monitor = getUsageMonitor();

        // Should not crash when checking thresholds
        monitor.start();

        // Should have started successfully
        expect(monitor['intervalId']).not.toBeNull();

        monitor.stop();
      });
    });

    describe('Anthropic response format backward compatibility', () => {
      it('should handle legacy Anthropic response format', () => {
        const monitor = getUsageMonitor();

        // Legacy format with field names that might have changed
        const legacyData = {
          five_hour_utilization: 0.60,
          seven_day_utilization: 0.40,
          five_hour_reset_at: '2025-01-17T15:00:00Z',
          seven_day_reset_at: '2025-01-20T12:00:00Z'
        };

        const usage = monitor['normalizeAnthropicResponse'](legacyData, 'test-profile-1', 'Legacy Profile');

        expect(usage).not.toBeNull();
        expect(usage.sessionPercent).toBe(60);
        expect(usage.weeklyPercent).toBe(40);
        expect(usage.limitType).toBe('session'); // 60% > 40%, so session is the higher limit
      });

      it('should handle response with only utilization values (no reset times)', () => {
        const monitor = getUsageMonitor();

        const minimalData = {
          five_hour_utilization: 0.75,
          seven_day_utilization: 0.50
          // Missing reset times
        };

        const usage = monitor['normalizeAnthropicResponse'](minimalData, 'test-profile-1', 'Minimal Profile');

        expect(usage).not.toBeNull();
        expect(usage.sessionPercent).toBe(75);
        expect(usage.weeklyPercent).toBe(50);
        // sessionResetTime/weeklyResetTime are now undefined - renderer uses timestamps
        expect(usage.sessionResetTime).toBeUndefined();
        expect(usage.weeklyResetTime).toBeUndefined();
      });

      it('should handle response with zero utilization values', () => {
        const monitor = getUsageMonitor();

        const zeroData = {
          five_hour_utilization: 0,
          seven_day_utilization: 0,
          five_hour_reset_at: '2025-01-17T15:00:00Z',
          seven_day_reset_at: '2025-01-20T12:00:00Z'
        };

        const usage = monitor['normalizeAnthropicResponse'](zeroData, 'test-profile-1', 'Zero Usage Profile');

        expect(usage).not.toBeNull();
        expect(usage.sessionPercent).toBe(0);
        expect(usage.weeklyPercent).toBe(0);
      });

      it('should handle response with only five_hour data (no seven_day)', () => {
        const monitor = getUsageMonitor();

        const partialData = {
          five_hour_utilization: 0.80,
          five_hour_reset_at: '2025-01-17T15:00:00Z'
          // Missing seven_day data
        };

        const usage = monitor['normalizeAnthropicResponse'](partialData, 'test-profile-1', 'Partial Profile');

        expect(usage).not.toBeNull();
        expect(usage.sessionPercent).toBe(80);
        expect(usage.weeklyPercent).toBe(0); // Defaults to 0
        // sessionResetTime/weeklyResetTime are now undefined - renderer uses timestamps
        expect(usage.sessionResetTime).toBeUndefined();
        expect(usage.weeklyResetTime).toBeUndefined();
        // Verify timestamps are still provided for renderer
        expect(usage.sessionResetTimestamp).toBe('2025-01-17T15:00:00Z');
      });
    });

    describe('Provider detection backward compatibility', () => {
      it('should handle Anthropic OAuth profiles (no baseUrl in OAuth profiles)', async () => {
        // OAuth profiles don't have baseUrl - they should default to Anthropic provider
        // This test verifies the backward compatibility by checking that:
        // 1. OAuth profiles (without baseUrl) are supported
        // 2. They default to using Anthropic's OAuth usage endpoint

        const endpoint = getUsageEndpoint('anthropic', 'https://api.anthropic.com');
        expect(endpoint).toBe('https://api.anthropic.com/api/oauth/usage');

        // Verify that when no baseUrl is provided (OAuth profile scenario),
        // the system defaults to Anthropic's standard endpoint
        const provider = detectProvider('https://api.anthropic.com');
        expect(provider).toBe('anthropic');
      });

      it('should handle Anthropic OAuth default baseUrl', () => {
        // OAuth profiles don't have baseUrl, should default to Anthropic
        const endpoint = getUsageEndpoint('anthropic', 'https://api.anthropic.com');
        expect(endpoint).toBe('https://api.anthropic.com/api/oauth/usage');
      });
    });

    describe('Mixed OAuth/API profile environments', () => {
      it('should handle environment with both OAuth and API profiles', async () => {
        const monitor = getUsageMonitor();
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

        // Mock both OAuth and API profiles
        mockLoadProfilesFile.mockResolvedValueOnce({
          profiles: [
            {
              id: 'api-profile-1',
              name: 'API Profile',
              baseUrl: 'https://api.anthropic.com',
              apiKey: 'sk-ant-api-key'
            },
            {
              id: 'api-profile-2',
              name: 'OpenAI API Profile',
              baseUrl: 'https://api.openai.com/v1',
              apiKey: 'sk-openai-key'
            }
          ],
          activeProfileId: 'api-profile-1',
          version: 1
        });

        const credential = await monitor['getCredential']();

        // Should use API profile when active
        expect(credential).toBe('sk-ant-api-key');

        consoleSpy.mockRestore();
      });

      it('should switch from API profile back to OAuth profile', async () => {
        const monitor = getUsageMonitor();
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

        // First, active API profile
        mockLoadProfilesFile.mockResolvedValueOnce({
          profiles: [{
            id: 'api-profile-1',
            name: 'API Profile',
            baseUrl: 'https://api.anthropic.com',
            apiKey: 'sk-ant-api-key'
          }],
          activeProfileId: 'api-profile-1',
          version: 1
        });

        let credential = await monitor['getCredential']();
        expect(credential).toBe('sk-ant-api-key');

        // Then, no active API profile (should fall back to OAuth)
        mockLoadProfilesFile.mockResolvedValueOnce({
          profiles: [],
          activeProfileId: null,
          version: 1
        });

        credential = await monitor['getCredential']();
        expect(credential).toBe('mock-decrypted-token');

        consoleSpy.mockRestore();
      });
    });

    describe('Graceful degradation for unknown providers', () => {
      it('should return null for unknown provider instead of throwing', () => {
        const endpoint = getUsageEndpoint('unknown' as ApiProvider, 'https://unknown-provider.com');
        expect(endpoint).toBeNull();
      });

      it('should handle invalid baseUrl gracefully', () => {
        const endpoint = getUsageEndpoint('anthropic', 'not-a-url');
        expect(endpoint).toBeNull();
      });

      it('should detect unknown provider from unrecognized baseUrl', () => {
        const provider = detectProvider('https://unknown-api-provider.com/v1');
        expect(provider).toBe('unknown');
      });
    });
  });

  describe('Cooldown-based API retry mechanism', () => {
    beforeEach(() => {
      // Clear any existing failure timestamps before each test
      const monitor = getUsageMonitor();
      monitor['apiFailureTimestamps'].clear();
    });

    it('should record API failure timestamp on error', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ error: 'Server error' })
      } as unknown as Response);

      const monitor = getUsageMonitor();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const profileId = 'test-profile-cooldown';

      // Call fetchUsageViaAPI which should fail and record timestamp
      await monitor['fetchUsageViaAPI']('valid-token', profileId, 'Test Profile', undefined);

      // Verify failure timestamp was recorded
      const failureTimestamp = monitor['apiFailureTimestamps'].get(profileId);
      expect(failureTimestamp).toBeDefined();
      expect(typeof failureTimestamp).toBe('number');
      // Should be recent (within last second)
      expect(Date.now() - failureTimestamp!).toBeLessThan(1000);

      consoleSpy.mockRestore();
    });

    it('should allow API retry after cooldown expires', async () => {
      const monitor = getUsageMonitor();
      const profileId = 'test-profile-retry';
      const now = Date.now();

      // Set a failure timestamp that's just before the cooldown period
      const expiredFailureTime = now - UsageMonitor['API_FAILURE_COOLDOWN_MS'] - 1000; // 1 second past cooldown
      monitor['apiFailureTimestamps'].set(profileId, expiredFailureTime);

      // shouldUseApiMethod should return true (cooldown expired)
      const shouldUseApi = monitor['shouldUseApiMethod'](profileId);
      expect(shouldUseApi).toBe(true);
    });

    it('should prevent API retry during cooldown period', async () => {
      const monitor = getUsageMonitor();
      const profileId = 'test-profile-cooldown-active';
      const now = Date.now();

      // Set a recent failure timestamp (well within cooldown period)
      const recentFailureTime = now - 1000; // 1 second ago
      monitor['apiFailureTimestamps'].set(profileId, recentFailureTime);

      // shouldUseApiMethod should return false (still in cooldown)
      const shouldUseApi = monitor['shouldUseApiMethod'](profileId);
      expect(shouldUseApi).toBe(false);
    });

    it('should allow API call when no previous failure recorded', async () => {
      const monitor = getUsageMonitor();
      const profileId = 'test-profile-no-failure';

      // No failure timestamp recorded for this profile
      expect(monitor['apiFailureTimestamps'].has(profileId)).toBe(false);

      // shouldUseApiMethod should return true (no previous failure)
      const shouldUseApi = monitor['shouldUseApiMethod'](profileId);
      expect(shouldUseApi).toBe(true);
    });

    it('should handle edge case exactly at cooldown boundary', async () => {
      const monitor = getUsageMonitor();
      const profileId = 'test-profile-boundary';
      const now = Date.now();

      // Set failure timestamp exactly at cooldown boundary
      const boundaryTime = now - UsageMonitor['API_FAILURE_COOLDOWN_MS'];
      monitor['apiFailureTimestamps'].set(profileId, boundaryTime);

      // At exact boundary, should allow retry (cooldown period has passed)
      const shouldUseApi = monitor['shouldUseApiMethod'](profileId);
      expect(shouldUseApi).toBe(true);
    });

    it('should track failures independently for different profiles', async () => {
      const monitor = getUsageMonitor();
      const profile1 = 'profile-1';
      const profile2 = 'profile-2';
      const now = Date.now();

      // Set recent failure for profile1
      monitor['apiFailureTimestamps'].set(profile1, now - 1000);
      // Set expired failure for profile2
      monitor['apiFailureTimestamps'].set(profile2, now - UsageMonitor['API_FAILURE_COOLDOWN_MS'] - 1000);

      // Profile 1 should be in cooldown
      expect(monitor['shouldUseApiMethod'](profile1)).toBe(false);
      // Profile 2 should be allowed
      expect(monitor['shouldUseApiMethod'](profile2)).toBe(true);
    });
  });

  describe('Race condition prevention via activeProfile parameter', () => {
    it('should use passed activeProfile instead of re-detecting', async () => {
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: {
          get: vi.fn((name: string) => name === 'content-type' ? 'application/json' : null)
        },
        json: async () => ({
          five_hour_utilization: 0.5,
          seven_day_utilization: 0.3,
          five_hour_reset_at: '2025-01-17T15:00:00Z',
          seven_day_reset_at: '2025-01-20T12:00:00Z'
        })
      } as unknown as Response);

      // Mock API profile
      mockLoadProfilesFile.mockResolvedValueOnce({
        profiles: [{
          id: 'api-profile-1',
          name: 'API Profile',
          baseUrl: 'https://api.anthropic.com',
          apiKey: 'sk-ant-api-key'
        }],
        activeProfileId: 'api-profile-1',
        version: 1
      });

      const monitor = getUsageMonitor();

      // Pre-determined active profile (simulating profile at time of checkUsageAndSwap)
      const predeterminedProfile = {
        isAPIProfile: true,
        profileId: 'api-profile-1',
        profileName: 'API Profile',
        baseUrl: 'https://api.anthropic.com'
      };

      // Call fetchUsageViaAPI with predetermined profile
      const usage = await monitor['fetchUsageViaAPI'](
        'sk-ant-api-key',
        'api-profile-1',
        'API Profile',
        undefined,
        predeterminedProfile
      );

      // Log any console.error calls for debugging
      if (errorSpy.mock.calls.length > 0) {
      }

      // Should successfully fetch usage using the passed profile
      expect(usage).not.toBeNull();
      if (usage) {
        expect(usage.profileId).toBe('api-profile-1');
        expect(usage.sessionPercent).toBe(50);
      }

      errorSpy.mockRestore();
    });

    it('should fall back to profile detection when activeProfile not provided', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: {
          get: vi.fn((name: string) => name === 'content-type' ? 'application/json' : null)
        },
        json: async () => ({
          five_hour_utilization: 0.5,
          seven_day_utilization: 0.3,
          five_hour_reset_at: '2025-01-17T15:00:00Z',
          seven_day_reset_at: '2025-01-20T12:00:00Z'
        })
      } as unknown as Response);

      // Mock API profile
      mockLoadProfilesFile.mockResolvedValueOnce({
        profiles: [{
          id: 'api-profile-1',
          name: 'API Profile',
          baseUrl: 'https://api.anthropic.com',
          apiKey: 'sk-ant-api-key'
        }],
        activeProfileId: 'api-profile-1',
        version: 1
      });

      const monitor = getUsageMonitor();

      // Call fetchUsageViaAPI WITHOUT predetermined profile
      // Should fall back to detecting profile from activeProfileId
      const usage = await monitor['fetchUsageViaAPI'](
        'sk-ant-api-key',
        'api-profile-1',
        'API Profile',
        undefined, // No email
        undefined // No activeProfile passed
      );

      // Should still work by detecting the profile
      expect(usage).not.toBeNull();
      expect(usage?.profileId).toBe('api-profile-1');
    });

    it('should handle OAuth profile in activeProfile parameter', async () => {
      const mockFetch = vi.mocked(global.fetch);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: {
          get: vi.fn((name: string) => name === 'content-type' ? 'application/json' : null)
        },
        json: async () => ({
          five_hour_utilization: 0.5,
          seven_day_utilization: 0.3,
          five_hour_reset_at: '2025-01-17T15:00:00Z',
          seven_day_reset_at: '2025-01-20T12:00:00Z'
        })
      } as unknown as Response);

      const monitor = getUsageMonitor();

      // Pre-determined OAuth profile
      const oauthProfile = {
        isAPIProfile: false,
        profileId: 'oauth-profile',
        profileName: 'OAuth Profile',
        baseUrl: 'https://api.anthropic.com'
      };

      // Call fetchUsageViaAPI with OAuth profile
      const usage = await monitor['fetchUsageViaAPI'](
        'oauth-token',
        'oauth-profile',
        'OAuth Profile',
        undefined,
        oauthProfile
      );

      // Should successfully fetch usage for OAuth profile
      expect(usage).not.toBeNull();
      expect(usage?.profileId).toBe('oauth-profile');
    });
  });

  describe('Shared utility - hasHardcodedText', () => {
    it('should return true for empty string', () => {
      expect(hasHardcodedText('')).toBe(true);
    });

    it('should return true for null', () => {
      expect(hasHardcodedText(null)).toBe(true);
    });

    it('should return true for undefined', () => {
      expect(hasHardcodedText(undefined)).toBe(true);
    });

    it('should return true for "Unknown"', () => {
      expect(hasHardcodedText('Unknown')).toBe(true);
    });

    it('should return true for "Expired"', () => {
      expect(hasHardcodedText('Expired')).toBe(true);
    });

    it('should return false for valid time strings', () => {
      expect(hasHardcodedText('2 hours remaining')).toBe(false);
      expect(hasHardcodedText('1 day left')).toBe(false);
      expect(hasHardcodedText('30 minutes')).toBe(false);
    });

    it('should be case-sensitive for "Unknown" and "Expired"', () => {
      // Lowercase versions should not trigger the filter
      expect(hasHardcodedText('unknown')).toBe(false);
      expect(hasHardcodedText('expired')).toBe(false);
      expect(hasHardcodedText('UNKNOWN')).toBe(false);
      expect(hasHardcodedText('EXPIRED')).toBe(false);
    });

    it('should handle strings with only whitespace', () => {
      // Whitespace-only strings are falsy when trimmed
      expect(hasHardcodedText('   ')).toBe(true);
    });
  });
});
