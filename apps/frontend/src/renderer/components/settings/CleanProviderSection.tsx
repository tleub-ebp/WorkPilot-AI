import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { SettingsSection } from './SettingsSection';
import { CleanProviderGrid } from './CleanProviderGrid';
import { getAllConnectors } from './multiconnector/utils';
import { Loader2, AlertCircle, Info, X, Activity } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Dialog, DialogContent } from '../ui/dialog';
import { GlobalAutoSwitching } from './GlobalAutoSwitching';
import { ProviderConfigDialog } from './ProviderConfigDialog';
import { getStaticProviders, type CanonicalProvider } from '@shared/utils/providers';
import { getProvider as getRegistryProvider } from '@shared/services/providerRegistry';
import { useSettingsStore } from '@/stores/settings-store';
import { useToast } from '@/hooks/use-toast';
import { ProviderService } from '@shared/services/providerService';
import type { ProfileUsageSummary, AuthMethod } from '@shared/types/agent';

interface Provider {
  id: string;
  name: string;
  category: string;
  description?: string;
  isConfigured: boolean;
  isWorking?: boolean;
  lastTested?: string;
  usageCount?: number;
  isPremium?: boolean;
  icon?: React.ReactNode;
  // Real data fields
  realUsageData?: ProfileUsageSummary;
  realApiKeyInfo?: {
    hasKey: boolean;
    keyPreview?: string;
    provider?: string;
    isOAuth?: boolean;
    authMethod?: AuthMethod;
  };
}

interface CleanProviderSectionProps {
  settings: any;
  onSettingsChange: (settings: any) => void;
  isOpen: boolean;
}

const providerCategories: Record<string, string> = {
  'anthropic': 'independent',
  'claude': 'independent',
  'openai': 'openai',
  'ollama': 'independent',
  'gemini': 'google',
  'google': 'google',
  'meta-llama': 'meta',
  'meta': 'meta',
  'mistral': 'independent',
  'deepseek': 'independent',
  'grok': 'independent',
  'windsurf': 'independent',
  'cursor': 'independent',
  'copilot': 'independent',
  'aws': 'microsoft',
  'azure-openai': 'microsoft',
};

export function CleanProviderSection({ 
  settings: propsSettings, 
  onSettingsChange: propsOnSettingsChange, 
  isOpen 
}: Readonly<CleanProviderSectionProps>) {
  const { t } = useTranslation('settings');
  const { t: tCommon } = useTranslation('common');
  const { toast } = useToast();
  const [connectors, setConnectors] = useState<Array<{ id: string, label: string }>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testingProviders, setTestingProviders] = useState<Set<string>>(new Set());
  const [autoSwitchingOpen, setAutoSwitchingOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [providersState, setProvidersState] = useState<Provider[]>([]);
  
  // Real data states
  const [profileUsageData, setProfileUsageData] = useState<Map<string, ProfileUsageSummary>>(new Map());
  const [providerTestResults, setProviderTestResults] = useState<Map<string, { date: string; success: boolean }>>(new Map());

  // Use store directly for real-time updates (like ProviderSelector)
  const { profiles, settings: storeSettings, updateSettings } = useSettingsStore();
  
  // Create a unified settings object and onSettingsChange that updates both props and store
  const settings = storeSettings;
  const onSettingsChange = async (newSettings: any) => {
    // Update props for backward compatibility
    propsOnSettingsChange(newSettings);
    // Update store for real-time sync across components
    updateSettings(newSettings);
  };

  // Load real data when section is opened (runs once when panel opens)
  useEffect(() => {
    if (isOpen) {
      loadConnectors();
      loadProfileUsageData();
      loadProviderTestResults();
    }
  }, [isOpen]);

  // Load connectors
  const loadConnectors = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const connectors = await getAllConnectors();
      setConnectors(connectors);
    } catch (err) {
      console.error('Failed to load connectors:', err);
      setError(t('sections.accounts.providers.loadError'));
      setConnectors([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Load profile usage data
  const loadProfileUsageData = async () => {
    try {
      const result = await globalThis.electronAPI.requestAllProfilesUsage?.(true);
      if (result?.success && result.data) {
        const usageMap = new Map<string, ProfileUsageSummary>();
        result.data.allProfiles.forEach((profile: ProfileUsageSummary) => {
          usageMap.set(profile.profileId, profile);
        });
        setProfileUsageData(usageMap);
      }
    } catch (err) {
      console.warn('[CleanProviderSection] Failed to load profile usage data:', err);
    }
  };

  // Load provider test results from settings or backend
  const loadProviderTestResults = async () => {
    try {
      // For now, we'll simulate loading test results
      // In a real implementation, this would load from a backend API or settings
      const testResults = new Map<string, { date: string; success: boolean }>();
      
      // Check if we have any recent test results in settings
      Object.keys(settings).forEach(key => {
        if (key.startsWith('testResult_')) {
          const providerId = key.replace('testResult_', '');
          const result = (settings as any)[key];
          if (result?.date) {
            testResults.set(providerId, {
              date: result.date,
              success: result.success || false
            });
          }
        }
      });
      
      setProviderTestResults(testResults);
    } catch (err) {
      console.warn('[CleanProviderSection] Failed to load provider test results:', err);
    }
  };

  // Determine the auth method for a provider using providerRegistry as source of truth
  const getProviderAuthMethod = (providerId: string): AuthMethod => {
    const registryProvider = getRegistryProvider(providerId);
    if (registryProvider) {
      if (registryProvider.requiresCLI) return 'cli';
      if (registryProvider.requiresOAuth && !registryProvider.requiresApiKey) return 'oauth';
      if (!registryProvider.requiresApiKey && !registryProvider.requiresOAuth && !registryProvider.requiresCLI) return 'local';
    }
    return 'api-key';
  };

  // Get API key info for a provider
  const getApiKeyInfo = (providerId: string): { hasKey: boolean; keyPreview?: string; provider?: string; isOAuth?: boolean; authMethod?: AuthMethod } => {
    // Determine auth method from registry
    const authMethod = getProviderAuthMethod(providerId);
    const isOAuthOrCLI = authMethod === 'cli' || authMethod === 'oauth';

    // Special handling for OAuth providers like Windsurf that don't need profiles
    if (isOAuthOrCLI && providerId === 'windsurf') {
      // Check if Windsurf OAuth token is available via backend status
      const isConfigured = providerStatus[providerId] || false;
      if (isConfigured) {
        return {
          hasKey: true,
          keyPreview: undefined,
          provider: 'Windsurf OAuth',
          isOAuth: true,
          authMethod: 'oauth'
        };
      }
    }

    // Check profiles for API keys
    const profile = profiles.find(p => {
      if (!p.baseUrl) return false;
      const detectedProvider = detectProviderFromUrl(p.baseUrl);
      return detectedProvider === providerId ||
             (providerId === 'claude' && detectedProvider === 'anthropic') ||
             (providerId === 'gemini' && p.baseUrl.includes('googleapis.com')) ||
             (providerId === 'google' && p.baseUrl.includes('googleapis.com'));
    });

    if (profile?.apiKey) {
      return {
        hasKey: true,
        keyPreview: maskApiKey(profile.apiKey),
        provider: profile.name,
        isOAuth: false,
        authMethod: 'api-key'
      };
    }

    // Check settings for API keys (for providers like OpenAI, etc.)
    const apiKeyField = getProviderApiKeyField(providerId);
    if (apiKeyField && (settings as any)[apiKeyField]) {
      return {
        hasKey: true,
        keyPreview: maskApiKey((settings as any)[apiKeyField]),
        isOAuth: false,
        authMethod: 'api-key'
      };
    }

    // For other OAuth/CLI providers, check if they are configured (even without API key)
    if (isOAuthOrCLI && profile) {
      return {
        hasKey: true,
        keyPreview: undefined,
        provider: profile.name,
        isOAuth: true,
        authMethod
      };
    }

    // For local providers (e.g. Ollama), mark as configured without a key
    if (authMethod === 'local') {
      return {
        hasKey: true,
        keyPreview: undefined,
        isOAuth: false,
        authMethod: 'local'
      };
    }

    return { hasKey: false, authMethod };
  };

  // Helper function to detect provider from URL
  const detectProviderFromUrl = (url: string): string => {
    const urlLower = url.toLowerCase();
    if (urlLower.includes('api.anthropic.com')) return 'anthropic';
    if (urlLower.includes('api.openai.com')) return 'openai';
    if (urlLower.includes('googleapis.com')) return 'google';
    if (urlLower.includes('api.mistral.ai')) return 'mistral';
    if (urlLower.includes('api.deepseek.com')) return 'deepseek';
    if (urlLower.includes('api.x.ai')) return 'grok';
    if (urlLower.includes('api.meta.ai')) return 'meta';
    if (urlLower.includes('windsurf.com') || urlLower.includes('codeium.com')) return 'windsurf';
    return 'unknown';
  };

  // Helper function to get API key field for provider
  const getProviderApiKeyField = (providerId: string): string | null => {
    const apiKeyMap: Record<string, string> = {
      'openai': 'globalOpenAIApiKey',
      'gemini': 'globalGoogleApiKey',
      'google': 'globalGoogleDeepMindApiKey',
      'meta': 'globalMetaApiKey',
      'meta-llama': 'globalMetaLlamaApiKey',
      'mistral': 'globalMistralApiKey',
      'deepseek': 'globalDeepSeekApiKey',
      'grok': 'globalGrokApiKey',
      'windsurf': 'globalWindsurfApiKey',
      'cursor': 'globalCursorApiKey',
      'aws': 'globalAWSApiKey',
      'azure-openai': 'globalOpenAIApiKey',
    };
    return apiKeyMap[providerId] || null;
  };

  // Helper function to mask API key
  const maskApiKey = (apiKey: string): string => {
    if (!apiKey || apiKey.length < 10) return 'sk-...';
    return `sk-${apiKey.substring(3, 7)}...••••••••••••••••••••••••••••`;
  };

  // Utiliser la même logique que ProviderSelector pour déterminer le statut
  const [staticProviders, setStaticProviders] = useState<CanonicalProvider[]>([]);
  const [providerStatus, setProviderStatus] = useState<Record<string, boolean>>({});

  // Charger les providers de manière asynchrone
  useEffect(() => {
    const loadProviders = async () => {
      try {
        // Enrich settings with Claude OAuth status from CLI config files (main process)
        const enrichedSettings = { ...settings };
        try {
          if (globalThis.electronAPI?.checkClaudeOAuth) {
            const oauthResult = await globalThis.electronAPI.checkClaudeOAuth();
            if (oauthResult.isAuthenticated) {
              enrichedSettings.globalClaudeOAuthToken = oauthResult.profileName || 'oauth-authenticated';
            }
          }
        } catch {
          // IPC not available
        }
        const result = await getStaticProviders(profiles, enrichedSettings);
        setStaticProviders(result.providers);
        setProviderStatus(result.status);
      } catch (error) {
        console.error('Failed to load providers:', error);
      }
    };
    
    loadProviders();
  }, [profiles, settings]);

  // Transformer les providers statiques en providers pour la grille avec mémorisation
  const providers = useMemo(() => {
    return staticProviders.map(provider => {
      // Get real usage data for this provider
      const usageData = Array.from(profileUsageData.values()).find(profile => 
        profile.profileName?.toLowerCase().includes(provider.name.toLowerCase()) ||
        profile.profileId.includes(provider.name)
      );

      // Get test result for this provider
      const testResult = providerTestResults.get(provider.name);

      // Get API key info for this provider
      const apiKeyInfo = getApiKeyInfo(provider.name);

      const mappedProvider = {
        id: provider.name,
        name: provider.label,
        category: providerCategories[provider.name] || 'independent',
        description: t(`sections.accounts.providers.${provider.name}`) || provider.description,
        isConfigured: providerStatus[provider.name] || false,
        isWorking: providerStatus[provider.name] ? true : undefined,
        // Use real data instead of dummy data
        lastTested: testResult?.date,
        usageCount: usageData?.sessionPercent ? Math.round(usageData.sessionPercent) : undefined,
        isPremium: ['anthropic', 'claude', 'openai', 'gemini'].includes(provider.name),
        // Add real data fields
        realUsageData: usageData,
        realApiKeyInfo: apiKeyInfo,
      };
      
      return mappedProvider;
    });
  }, [staticProviders, providerStatus, profileUsageData, providerTestResults, profiles, t]);

  // Synchronize providersState with providers (avoid infinite loop)
  useEffect(() => {
    setProvidersState(providers);
  }, [providers.length, providers.map(p => `${p.id}-${p.isConfigured}-${p.lastTested}`).join(',')]);

  const handleConfigure = (providerId: string) => {
    const provider = providers.find(p => p.id === providerId);
    if (provider) {
      setSelectedProvider(provider);
      setConfigDialogOpen(true);
    }
  };

  const handleTest = async (providerId: string) => {
    setTestingProviders(prev => new Set(prev).add(providerId));
    
    try {
      // Passer les profiles actuels au ProviderService
      const currentProfiles = getCurrentProfiles();
      ProviderService.setProfiles(currentProfiles);

      // Utiliser le vrai service de test du provider
      const result = await ProviderService.testProvider(providerId);

      // Save test result
      const testResult = {
        date: new Date().toISOString(),
        success: result.success
      };

      // Update provider test results
      setProviderTestResults(prev => new Map(prev).set(providerId, testResult));

      // Save to settings for persistence
      onSettingsChange({
        ...settings,
        [`testResult_${providerId}`]: testResult
      });

      if (result.success) {
        // Mettre à jour le statut du provider pour indiquer qu'il fonctionne
        setProviderStatus(prev => ({
          ...prev,
          [providerId]: true
        }));
        
        // Afficher un toast de succès avec détails
        let description = t('sections.accounts.providerCard.testSuccessDescription', { 
          providerName: providerId 
        });
        
        if (result.details) {
          if (result.details.modelCount) {
            description += ` (${t('sections.accounts.providerCard.testDetails.modelsAvailable', { count: result.details.modelCount })})`;
          } else if (result.details.model) {
            description += ` (${t('sections.accounts.providerCard.testDetails.modelUsed', { model: result.details.model })})`;
          }
        }
        
        toast({
          title: t('sections.accounts.providerCard.testSuccess'),
          description,
        });
        
        // Test provider success
      } else {
        // Afficher un toast d'erreur avec le message réel de l'API
        toast({
          variant: 'destructive',
          title: t('sections.accounts.providerCard.testError'),
          description: t('sections.accounts.providerCard.testErrorDescription', { 
            providerName: providerId,
            error: result.message
          }),
        });
        
        console.error('Test failed:', providerId, result.message);
      }
      
    } catch (err) {
      console.error('Test error:', err);
      
      // Afficher un toast d'erreur générique
      toast({
        variant: 'destructive',
        title: t('sections.accounts.providerCard.testError'),
        description: t('sections.accounts.providerCard.testErrorDescription', { 
          providerName: providerId,
          error: t('sections.accounts.providerCard.errors.unknownError')
        }),
      });
    } finally {
      setTestingProviders(prev => {
        const newSet = new Set(prev);
        newSet.delete(providerId);
        return newSet;
      });
    }
  };

  // Récupérer les profiles actuels pour le test
  const getCurrentProfiles = () => {
    const { profiles } = useSettingsStore.getState();
    return profiles;
  };

  const handleToggle = async (providerId: string, enabled: boolean) => {
    try {

      // Get the current provider configuration
      const currentConfig = await ProviderService.getUserProviderConfig(providerId) || {};

      // Update the enabled status in the configuration
      const updatedConfig = {
        ...currentConfig,
        enabled: enabled,
        lastUpdated: new Date().toISOString()
      };

      // Save the updated configuration
      await ProviderService.saveUserProviderConfig(providerId, updatedConfig);

      // Update the local providers state to reflect the change
      setProvidersState((prevProviders: Provider[]) =>
        prevProviders.map((provider: Provider) =>
          provider.id === providerId
            ? { ...provider, isWorking: !!enabled }
            : provider
        )
      );

      // Update disabledAutoSwitchProviders setting
      // Note: providerPriorityOrder is now managed solely by ClaudeProfileManager
      const updatedSettings = { ...settings };
      const currentDisabled = updatedSettings.disabledAutoSwitchProviders || [];
      if (enabled) {
        // Enable provider: remove from disabled list
        updatedSettings.disabledAutoSwitchProviders = currentDisabled.filter((id: string) => id !== providerId);
      } else if (!currentDisabled.includes(providerId)) {
        // Disable provider: add to disabled list if not already there
        updatedSettings.disabledAutoSwitchProviders = [...currentDisabled, providerId];
      }

      // Single atomic settings update
      onSettingsChange(updatedSettings);

      // Show toast notification
      toast({
        title: enabled ? t('sections.accounts.providerToggle.enabled') : t('sections.accounts.providerToggle.disabled'),
        description: t('sections.accounts.providerToggle.description', {
          providerId: providerId,
          action: enabled ? tCommon('actions.enabled') : tCommon('actions.disabled')
        }),
      });

    } catch (error) {
      console.error('Failed to toggle provider:', error);
      toast({
        variant: 'destructive',
        title: t('sections.accounts.providerToggle.error'),
        description: t('sections.accounts.providerToggle.errorDescription', {
          providerId: providerId,
          action: enabled ? tCommon('actions.enable') : tCommon('actions.disable')
        }),
      });
    }
  };

  const handleRemove = () => {
    // Pour l'instant, on ne fait rien car on utilise les profiles
    // Remove provider
  };

  const handleRefresh = () => {
    globalThis.location.reload();
  };

  if (isLoading) {
    return (
      <SettingsSection
        title={t('accounts.multiConnector.title')}
        description={t('accounts.multiConnector.description')}
      >
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          <span className="text-sm text-gray-600">AAChargement des providers...</span>
        </div>
      </SettingsSection>
    );
  }

  if (error) {
    return (
      <SettingsSection
        title={t('accounts.multiConnector.title')}
        description={t('accounts.multiConnector.description')}
      >
        <div className="space-y-4">
          <Alert className="border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-700">
              {error}
            </AlertDescription>
          </Alert>
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
          >
            Réessayer
          </Button>
        </div>
      </SettingsSection>
    );
  }

  return (
    <SettingsSection
      title={t('sections.accounts.multiConnector.title')}
      description={t('sections.accounts.multiConnector.description')}
    >
      <div className="space-y-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50/50 border border-red-100 rounded-lg">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          </div>
        )}

        <div className="flex gap-6">
          {/* Colonne de gauche - Providers (prend toute la largeur si auto-switching fermé) */}
          <div className={autoSwitchingOpen ? "flex-2" : "flex-1"}>
            {/* Alertes simples */}
          {providersState.filter(p => p.isConfigured).length === 0 && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                {t('sections.accounts.alerts.noProviders')}
              </AlertDescription>
            </Alert>
          )}

          {providersState.some(p => p.isWorking === false) && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {t('sections.accounts.alerts.providerErrors', { 
                  count: providersState.filter(p => p.isWorking === false).length 
                })}
              </AlertDescription>
            </Alert>
          )}

            {/* Grille de providers */}
            <CleanProviderGrid
              providers={providersState}
              onConfigure={handleConfigure}
              onTest={handleTest}
              onToggle={handleToggle}
              onRemove={handleRemove}
              isLoading={isLoading}
              isAutoSwitchingOpen={autoSwitchingOpen}
              testingProviders={testingProviders}
              settings={settings}
              onSettingsChange={onSettingsChange}
            />
          </div>

          {/* Auto-switching settings - tiroir compact */}
          <div className={`${autoSwitchingOpen ? "flex-1" : "w-auto"} transition-all duration-300`}>
            {autoSwitchingOpen ? (
              /* Contenu de l'auto-switching dans un tiroir */
              <div className="border rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    <h3 className="font-medium text-sm">{t('sections.accounts.autoSwitching.title')}</h3>
                  </div>
                  <Button
                    onClick={() => setAutoSwitchingOpen(false)}
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
                
                <div className="space-y-4">
                  <GlobalAutoSwitching 
                    settings={settings} 
                    onSettingsChange={onSettingsChange}
                    isOpen={true}
                    useSheet={true}
                  />
                </div>
              </div>
            ) : (
              /* Bouton compact pour ouvrir */
              <Button
                onClick={() => setAutoSwitchingOpen(true)}
                variant="outline"
                size="sm"
                className="h-8 px-3"
              >
                <Activity className="w-4 h-4 mr-2" />
                {t('sections.accounts.autoSwitching.title')}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Dialog de configuration - centré */}
      <Dialog open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
        <DialogContent className="max-w-[650px]">
          <ProviderConfigDialog
            isOpen={configDialogOpen}
            onOpenChange={setConfigDialogOpen}
            provider={selectedProvider}
            settings={settings}
            onSettingsChange={onSettingsChange}
            onTest={handleTest}
            useSheet={true}
          />
        </DialogContent>
      </Dialog>
    </SettingsSection>
  );
}
