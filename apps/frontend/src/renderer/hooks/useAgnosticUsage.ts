/**
 * Agnostic Usage Hook - Provider-agnostic usage data management
 * 
 * This hook provides a unified interface for managing usage data across all providers
 * and authentication methods, completely abstracting provider-specific details.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  AgnosticUsageData, 
  UsageError, 
  getProviderConfig,
  supportsAuthMethod 
} from '@shared/types/agnostic-usage';
import { 
  convertToAgnosticUsage,
  formatUsageValue,
  getUsageColorClass,
  getBadgeColorClasses,
  getGradientClass
} from '@shared/utils/agnostic-usage-converter';
import { credentialService, type CredentialConfig, type UsageData } from '@shared/services/credentialService';
import { useProviderContext } from '../components/ProviderContext';
import type { UsageSnapshot } from '@shared/types/agent';

export interface UseAgnosticUsageReturn {
  // Core state
  usageData: AgnosticUsageData | null;
  activeCredential: CredentialConfig | null;
  isLoading: boolean;
  isAvailable: boolean;
  error: UsageError | null;
  
  // Provider information
  providerConfig: ReturnType<typeof getProviderConfig>;
  selectedProvider: string;
  
  // Actions
  setActiveProvider: (provider: string, type: 'oauth' | 'api_key', profileId?: string) => Promise<void>;
  refreshUsageData: (provider?: string) => Promise<void>;
  validateCredentials: () => Promise<boolean>;
  testProvider: (provider: string) => Promise<{ success: boolean; message: string; details?: any }>;
  clearError: () => void;
  
  // Utility functions
  formatValue: (format?: 'percentage' | 'tokens' | 'cost' | 'custom') => string;
  getColorClass: (type?: 'text' | 'badge' | 'gradient') => string;
  getInitials: (name?: string) => string;
  
  // Status helpers
  needsReauth: boolean;
  isRateLimited: boolean;
  limitingPercent: number;
  sessionPercent: number;
  periodicPercent: number;
}

/**
 * Hook for managing agnostic usage data across all providers
 */
export function useAgnosticUsage(selectedProvider?: string): UseAgnosticUsageReturn {
  const { t } = useTranslation(['common']);
  const { selectedProvider: contextProvider } = useProviderContext();
  const provider = selectedProvider || contextProvider || t('agnosticUsage.providerGeneric', 'generic');
  const providerConfig = getProviderConfig(provider);
  
  // State
  const [usageData, setUsageData] = useState<AgnosticUsageData | null>(null);
  const [activeCredential, setActiveCredential] = useState<CredentialConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAvailable, setIsAvailable] = useState(false);
  const [error, setError] = useState<UsageError | null>(null);

  /**
   * Convert legacy UsageData to AgnosticUsageData
   */
  const convertLegacyUsageData = useCallback((legacyData: UsageData): AgnosticUsageData | null => {
    try {
      // If it's already in agnostic format, return as-is
      if ('metrics' in legacyData && 'provider' in legacyData) {
        return legacyData as unknown as AgnosticUsageData;
      }
      
      // Convert from UsageSnapshot format
      const snapshot: UsageSnapshot = {
        sessionPercent: legacyData.usage.sessionPercent || 0,
        weeklyPercent: legacyData.usage.weeklyPercent || 0,
        sessionResetTime: undefined, // Not available in legacy format
        weeklyResetTime: undefined, // Not available in legacy format
        sessionResetTimestamp: legacyData.usage.sessionResetTimestamp?.toString(),
        weeklyResetTimestamp: legacyData.usage.weeklyResetTimestamp?.toString(),
        profileId: legacyData.profileId || '',
        profileName: legacyData.profileName || '',
        profileEmail: (legacyData as any).profileEmail,
        fetchedAt: new Date(legacyData.timestamp),
        needsReauthentication: legacyData.usage.needsReauthentication,
        providerName: legacyData.provider,
        sessionUsageValue: legacyData.usage.sessionUsageValue,
        sessionUsageLimit: undefined, // Not available in legacy format
        weeklyUsageValue: legacyData.usage.weeklyUsageValue,
        weeklyUsageLimit: undefined, // Not available in legacy format
        usageWindows: undefined // Not available in legacy format
      };
      
      return convertToAgnosticUsage(snapshot);
    } catch (err) {
      console.error('[useAgnosticUsage] Failed to convert legacy data:', err);
      return null;
    }
  }, []);

  /**
   * Load initial data
   */
  const loadInitialData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load active credential
      const credential = await credentialService.getActiveCredential();
      setActiveCredential(credential);

      // Load usage data
      if (provider && provider !== 'generic') {
        const legacyUsage = await credentialService.getUsageData(provider);
        
        if (legacyUsage) {
          const agnosticUsage = convertLegacyUsageData(legacyUsage);
          if (agnosticUsage) {
            setUsageData(agnosticUsage);
            setIsAvailable(true);
            
            // Check for errors in the agnostic data
            if (agnosticUsage.error) {
              setError(agnosticUsage.error);
            }
          }
        } else {
          setIsAvailable(false);
        }
      }
      
      setIsLoading(false);
    } catch (err) {
      console.error('[useAgnosticUsage] Failed to load initial data:', err);
      
      // Convert error to UsageError format
      const usageError: UsageError = {
        code: 'LOAD_FAILED',
        message: t('agnosticUsage.loadFailed', 'Failed to load usage data'),
        provider,
        requiresAction: true,
        actionType: 'retry'
      };
      
      setError(usageError);
      setIsLoading(false);
      setIsAvailable(false);
    }
  }, [provider, convertLegacyUsageData, t]);

  /**
   * Set active provider
   */
  const handleSetActiveProvider = useCallback(async (providerName: string, type: 'oauth' | 'api_key', profileId?: string) => {
    try {
      setError(null);
      
      // Validate auth method support
      if (!supportsAuthMethod(providerName, type)) {
        const usageError: UsageError = {
          code: 'UNSUPPORTED_AUTH_METHOD',
          message: t('agnosticUsage.unsupportedAuthMethod', 'Provider {{provider}} does not support {{authMethod}} authentication', { provider: providerName, authMethod: type }),
          provider: providerName,
          requiresAction: true,
          actionType: 'configuration'
        };
        setError(usageError);
        return;
      }
      
      await credentialService.setActiveProvider(providerName, type, profileId);
      
      // Refresh usage data for the new provider
      if (providerName === provider) {
        const legacyUsage = await credentialService.getUsageData(providerName);
        if (legacyUsage) {
          const agnosticUsage = convertLegacyUsageData(legacyUsage);
          if (agnosticUsage) {
            setUsageData(agnosticUsage);
            setIsAvailable(true);
            if (agnosticUsage.error) {
              setError(agnosticUsage.error);
            }
          }
        }
      }
    } catch (err) {
      console.error('[useAgnosticUsage] Failed to set active provider:', err);
      
      const usageError: UsageError = {
        code: 'SET_PROVIDER_FAILED',
        message: t('agnosticUsage.setProviderFailed', 'Failed to set active provider'),
        provider: providerName,
        requiresAction: true,
        actionType: 'retry'
      };
      
      setError(usageError);
      throw err;
    }
  }, [provider, convertLegacyUsageData, t]);

  /**
   * Refresh usage data
   */
  const handleRefreshUsageData = useCallback(async (providerName?: string) => {
    try {
      setError(null);
      const targetProvider = providerName || provider;
      
      if (targetProvider && targetProvider !== 'generic') {
        const legacyUsage = await credentialService.getUsageData(targetProvider);
        if (legacyUsage) {
          const agnosticUsage = convertLegacyUsageData(legacyUsage);
          if (agnosticUsage) {
            setUsageData(agnosticUsage);
            setIsAvailable(true);
            if (agnosticUsage.error) {
              setError(agnosticUsage.error);
            }
          }
        }
      }
    } catch (err) {
      console.error('[useAgnosticUsage] Failed to refresh usage data:', err);
      
      const usageError: UsageError = {
        code: 'REFRESH_FAILED',
        message: t('agnosticUsage.refreshFailed', 'Failed to refresh usage data'),
        provider: providerName || provider,
        requiresAction: true,
        actionType: 'retry'
      };
      
      setError(usageError);
    }
  }, [provider, convertLegacyUsageData, t]);

  /**
   * Validate credentials
   */
  const handleValidateCredentials = useCallback(async (): Promise<boolean> => {
    try {
      setError(null);
      return await credentialService.validateCredentials();
    } catch (err) {
      console.error('[useAgnosticUsage] Failed to validate credentials:', err);
      
      const usageError: UsageError = {
        code: 'VALIDATION_FAILED',
        message: t('agnosticUsage.validationFailed', 'Failed to validate credentials'),
        provider,
        requiresAction: true,
        actionType: 'reauth'
      };
      
      setError(usageError);
      return false;
    }
  }, [provider, t]);

  /**
   * Test provider
   */
  const handleTestProvider = useCallback(async (providerName: string): Promise<{ success: boolean; message: string; details?: any }> => {
    try {
      setError(null);
      return await credentialService.testProvider(providerName);
    } catch (err) {
      console.error('[useAgnosticUsage] Failed to test provider:', err);
      
      const usageError: UsageError = {
        code: 'TEST_FAILED',
        message: t('agnosticUsage.testFailed', 'Failed to test provider'),
        provider: providerName,
        requiresAction: true,
        actionType: 'retry'
      };
      
      setError(usageError);
      return { success: false, message: usageError.message };
    }
  }, [t]);

  /**
   * Clear error
   */
  const handleClearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Format value based on provider and format
   */
  const handleFormatValue = useCallback((format?: 'percentage' | 'tokens' | 'cost' | 'custom') => {
    if (!usageData) return t('agnosticUsage.noUsageData', '0');
    return formatUsageValue(usageData, format);
  }, [usageData, t]);

  /**
   * Get color class based on usage
   */
  const handleGetColorClass = useCallback((type: 'text' | 'badge' | 'gradient' = 'text') => {
    if (!usageData) return type === 'badge' ? getBadgeColorClasses(0) : getUsageColorClass(0);
    
    const percent = usageData.metrics.periodicPercent;
    const needsReauth = usageData.needsReauthentication;
    
    switch (type) {
      case 'text':
        return getUsageColorClass(percent);
      case 'badge':
        return getBadgeColorClasses(percent, needsReauth);
      case 'gradient':
        return getGradientClass(percent);
      default:
        return getUsageColorClass(percent);
    }
  }, [usageData]);

  /**
   * Get initials from name
   */
  const handleGetInitials = useCallback((name?: string) => {
    if (!name || name.trim().length === 0) {
      return 'UN';
    }
    const words = name.trim().split(/\s+/);
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }, []);

  // Effects
  useEffect(() => {
    loadInitialData();

    // Subscribe to events
    const handleCredentialUpdated = (credential: CredentialConfig | null) => {
      setActiveCredential(credential);
    };

    const handleUsageChanged = (data: UsageData) => {
      if (!provider || data.provider === provider) {
        const agnosticUsage = convertLegacyUsageData(data);
        if (agnosticUsage) {
          setUsageData(agnosticUsage);
          setIsAvailable(true);
          setIsLoading(false);
          
          if (agnosticUsage.error) {
            setError(agnosticUsage.error);
          } else {
            setError(null);
          }
        }
      }
    };

    const handleProviderSwitched = (data: { provider: string; type: 'oauth' | 'api_key' }) => {
      if (data.provider === provider) {
        handleRefreshUsageData(data.provider);
      }
    };

    credentialService.on('credential:updated', handleCredentialUpdated);
    credentialService.on('usage:changed', handleUsageChanged);
    credentialService.on('provider:switched', handleProviderSwitched);

    return () => {
      credentialService.off('credential:updated', handleCredentialUpdated);
      credentialService.off('usage:changed', handleUsageChanged);
      credentialService.off('provider:switched', handleProviderSwitched);
    };
  }, [loadInitialData, provider, convertLegacyUsageData, handleRefreshUsageData]);

  // Computed values
  const needsReauth = usageData?.needsReauthentication || false;
  const isRateLimited = usageData?.isRateLimited || false;
  const limitingPercent = usageData ? Math.max(usageData.metrics.sessionPercent, usageData.metrics.periodicPercent) : 0;
  const sessionPercent = usageData?.metrics.sessionPercent || 0;
  const periodicPercent = usageData?.metrics.periodicPercent || 0;

  return {
    // Core state
    usageData,
    activeCredential,
    isLoading,
    isAvailable,
    error,
    
    // Provider information
    providerConfig,
    selectedProvider: provider,
    
    // Actions
    setActiveProvider: handleSetActiveProvider,
    refreshUsageData: handleRefreshUsageData,
    validateCredentials: handleValidateCredentials,
    testProvider: handleTestProvider,
    clearError: handleClearError,
    
    // Utility functions
    formatValue: handleFormatValue,
    getColorClass: handleGetColorClass,
    getInitials: handleGetInitials,
    
    // Status helpers
    needsReauth,
    isRateLimited,
    limitingPercent,
    sessionPercent,
    periodicPercent
  };
}
