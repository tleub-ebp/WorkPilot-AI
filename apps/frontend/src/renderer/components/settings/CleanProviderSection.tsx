import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { SettingsSection } from './SettingsSection';
import { CleanProviderGrid } from './CleanProviderGrid';
import { getAllConnectors } from './multiconnector/utils';
import { Loader2, AlertCircle, Info, X, Activity, CheckCircle, XCircle } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../ui/sheet';
import { GlobalAutoSwitching } from './GlobalAutoSwitching';
import { ProviderConfigDialog } from './ProviderConfigDialog';
import { getStaticProviders } from '@shared/utils/providers';
import { useSettingsStore } from '@/stores/settings-store';
import { useToast } from '@/hooks/use-toast';
import { ProviderService } from '@shared/services/providerService';
import type { APIProfile } from '@shared/types/profile';
import type { ProfileUsageSummary } from '@shared/types/agent';

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

const providerDescriptions: Record<string, string> = {
  'anthropic': 'Modèles Claude d\'Anthropic',
  'claude': 'Modèles Claude d\'Anthropic',
  'openai': 'Modèles GPT-5 et autres modèles OpenAI',
  'ollama': 'Modèles open-source locaux avec Ollama',
  'gemini': 'Modèles Gemini de Google DeepMind',
  'google': 'Accès aux API Google et Google DeepMind',
  'meta-llama': 'Modèles Llama de Meta via Together.ai',
  'meta': 'Modèles Meta AI officiels',
  'mistral': 'Modèles Mistral AI (Mistral, Codéal, etc.)',
  'deepseek': 'Modèles DeepSeek (DeepSeek-Coder, etc.)',
  'grok': 'Modèles Grok xAI',
  'windsurf': 'Provider Windsurf AI',
  'cursor': 'Provider Cursor AI',
  'copilot': 'GitHub Copilot',
  'aws': 'AWS Bedrock et services Amazon',
  'azure-openai': 'Modèles OpenAI via Azure',
};

export function CleanProviderSection({ 
  settings, 
  onSettingsChange, 
  isOpen 
}: CleanProviderSectionProps) {
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

  // Utiliser les profiles comme le ProviderSelector
  const { profiles, setActiveProfile } = useSettingsStore();

  // Track if we're in a manual toggle operation to avoid auto-sync conflicts
  const [isManualToggle, setIsManualToggle] = useState(false);

  // Load real data when section is opened
  useEffect(() => {
    if (isOpen) {
      loadConnectors();
      loadProfileUsageData();
      loadProviderTestResults();
      // Auto-sync configured providers with auto-switching
      if (!isManualToggle) {
        syncConfiguredProvidersWithAutoSwitching();
      }
    }
  }, [isOpen, providersState, isManualToggle]);

  // Auto-sync configured providers with auto-switching
  const syncConfiguredProvidersWithAutoSwitching = async () => {
    try {
      const currentSettings = { ...settings };
      
      // Initialize providerPriorityOrder if it doesn't exist
      if (!currentSettings.providerPriorityOrder) {
        currentSettings.providerPriorityOrder = [];
      }
      
      // Get all configured providers
      const configuredProviders = providersState.filter(p => p.isConfigured);
      
      // Add configured providers to auto-switching if not already present
      const updatedPriorityOrder = [...currentSettings.providerPriorityOrder];
      configuredProviders.forEach(provider => {
        if (!updatedPriorityOrder.includes(provider.id)) {
          updatedPriorityOrder.push(provider.id);
        }
      });
      
      // Remove unconfigured providers from auto-switching
      const finalPriorityOrder = updatedPriorityOrder.filter(providerId => 
        providersState.some(p => p.id === providerId && p.isConfigured)
      );
      
      // Update settings only if changed and not during a manual toggle operation
      if (JSON.stringify(currentSettings.providerPriorityOrder) !== JSON.stringify(finalPriorityOrder)) {
        currentSettings.providerPriorityOrder = finalPriorityOrder;
        onSettingsChange(currentSettings);
      }
      
    } catch (error) {
      console.error('Failed to sync configured providers with auto-switching:', error);
    }
  };

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
      const result = await window.electronAPI.requestAllProfilesUsage?.(true);
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
          const result = settings[key];
          if (result && result.date) {
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

  // Helper function to check if provider uses OAuth authentication
  const isProviderOAuth = (providerId: string): boolean => {
    // List of providers that typically use OAuth/CLI authentication
    const oauthProviders = [
      'copilot',      // GitHub Copilot CLI
      'cursor',       // Cursor CLI
      'windsurf',      // Windsurf CLI
      // Add other OAuth providers as needed
    ];
    
    return oauthProviders.includes(providerId);
  };

  // Get API key info for a provider
  const getApiKeyInfo = (providerId: string): { hasKey: boolean; keyPreview?: string; provider?: string; isOAuth?: boolean } => {
    // Check if provider uses OAuth authentication
    const isOAuthProvider = isProviderOAuth(providerId);
    
    // Check profiles for API keys
    const profile = profiles.find(p => {
      if (!p.baseUrl) return false;
      const detectedProvider = detectProviderFromUrl(p.baseUrl);
      return detectedProvider === providerId || 
             (providerId === 'claude' && detectedProvider === 'anthropic') ||
             (providerId === 'gemini' && p.baseUrl.includes('googleapis.com')) ||
             (providerId === 'google' && p.baseUrl.includes('googleapis.com'));
    });

    if (profile && profile.apiKey) {
      return {
        hasKey: true,
        keyPreview: maskApiKey(profile.apiKey),
        provider: profile.name,
        isOAuth: false
      };
    }

    // Check settings for API keys (for providers like OpenAI, etc.)
    const apiKeyField = getProviderApiKeyField(providerId);
    if (apiKeyField && settings[apiKeyField]) {
      return {
        hasKey: true,
        keyPreview: maskApiKey(settings[apiKeyField]),
        isOAuth: false
      };
    }

    // For OAuth providers, check if they are configured (even without API key)
    if (isOAuthProvider && profile) {
      return {
        hasKey: true,
        keyPreview: undefined,
        provider: profile.name,
        isOAuth: true
      };
    }

    return { hasKey: false };
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

  // Helper function to detect and sync providers with auto-switching
  const syncProviderWithAutoSwitching = async (providerId: string, action: 'add' | 'remove' | 'toggle', enabled?: boolean) => {
    try {
      console.log(`[AutoSwitching Sync] ${action} provider: ${providerId}, enabled: ${enabled}`);
      
      // Get current auto-switching settings
      const currentSettings = { ...settings };
      
      // Initialize providerPriorityOrder if it doesn't exist
      if (!currentSettings.providerPriorityOrder) {
        currentSettings.providerPriorityOrder = [];
      }
      
      console.log(`[AutoSwitching Sync] Current priority order:`, currentSettings.providerPriorityOrder);
      
      const providerName = staticProviders.find(p => p.name === providerId)?.label || providerId;
      
      if (action === 'add' || (action === 'toggle' && enabled === true)) {
        // Add provider to auto-switching priority list if not already present
        if (!currentSettings.providerPriorityOrder.includes(providerId)) {
          currentSettings.providerPriorityOrder = [...currentSettings.providerPriorityOrder, providerId];
          console.log(`[AutoSwitching Sync] Added ${providerId} to priority order`);
        } else {
          console.log(`[AutoSwitching Sync] ${providerId} already in priority order`);
        }
      } else if (action === 'remove' || (action === 'toggle' && enabled === false)) {
        // Remove provider from auto-switching priority list only if it exists
        const beforeCount = currentSettings.providerPriorityOrder.length;
        if (currentSettings.providerPriorityOrder.includes(providerId)) {
          currentSettings.providerPriorityOrder = currentSettings.providerPriorityOrder.filter((id: string) => id !== providerId);
          console.log(`[AutoSwitching Sync] Removed ${providerId} from priority order`);
        } else {
          console.log(`[AutoSwitching Sync] ${providerId} not in priority order, nothing to remove`);
        }
        const afterCount = currentSettings.providerPriorityOrder.length;
        console.log(`[AutoSwitching Sync] Priority order size changed: ${beforeCount} -> ${afterCount}`);
      }
      
      console.log(`[AutoSwitching Sync] Final priority order:`, currentSettings.providerPriorityOrder);
      
      // Update settings only if there's a change
      const currentPriorityOrder = settings.providerPriorityOrder || [];
      if (JSON.stringify(currentPriorityOrder) !== JSON.stringify(currentSettings.providerPriorityOrder)) {
        onSettingsChange(currentSettings);
        console.log(`[AutoSwitching Sync] Settings updated`);
      } else {
        console.log(`[AutoSwitching Sync] No change in settings, skipping update`);
      }
      
      // Show toast notification only for meaningful actions
      if (action === 'toggle' && enabled === true && !currentSettings.providerPriorityOrder.includes(providerId)) {
        toast({
          title: t('sections.accounts.autoSwitching.providerAdded'),
          description: t('sections.accounts.autoSwitching.providerDescription', { 
            providerName: providerName,
            action: tCommon('actions.add')
          }),
        });
      } else if (action === 'toggle' && enabled === false && currentSettings.providerPriorityOrder.includes(providerId)) {
        toast({
          title: t('sections.accounts.autoSwitching.providerRemoved'),
          description: t('sections.accounts.autoSwitching.providerDescription', { 
            providerName: providerName,
            action: tCommon('actions.delete')
          }),
        });
      }
      
    } catch (error) {
      console.error('Failed to sync provider with auto-switching:', error);
      toast({
        variant: 'destructive',
        title: t('sections.accounts.autoSwitching.syncError'),
        description: t('sections.accounts.autoSwitching.syncErrorDescription'),
      });
    }
  };

  // Utiliser la même logique que ProviderSelector pour déterminer le statut
  const { providers: staticProviders, status } = useMemo(
    () => getStaticProviders(profiles),
    [profiles]
  );

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
        isConfigured: status[provider.name] || false,
        isWorking: status[provider.name] ? true : undefined,
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
  }, [staticProviders, status, profileUsageData, providerTestResults, profiles, t]);

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
      // Vérifier si des profiles de test sont nécessaires et les ajouter
      const updatedProfiles = await ensureTestProfiles();

      // Passer les profiles mis à jour au ProviderService
      ProviderService.setProfiles(updatedProfiles);

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
        // TODO: Mettre à jour le statut dans le store ou l'état local
        
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

  // Fonction pour s'assurer que les profiles de test existent
  const ensureTestProfiles = async () => {
    const { profiles, saveProfile } = useSettingsStore.getState();
    
    // Profiles de test à ajouter
    const testProfiles = [
      {
        name: 'Anthropic Test',
        baseUrl: 'https://api.anthropic.com',
        apiKey: 'sk-ant-test-key-placeholder', // À remplacer par une vraie clé
      },
      {
        name: 'Google Gemini Test',
        baseUrl: 'https://generativelanguage.googleapis.com',
        apiKey: 'test-google-key-placeholder', // À remplacer par une vraie clé
      },
      {
        name: 'Mistral Test',
        baseUrl: 'https://api.mistral.ai',
        apiKey: 'test-mistral-key-placeholder', // À remplacer par une vraie clé
      }
    ];

    let addedProfiles = [];
    
    for (const testProfile of testProfiles) {
      const exists = profiles.some(p => 
        p.baseUrl === testProfile.baseUrl || 
        p.name === testProfile.name
      );
      
      if (!exists) {
        // Adding test profile
        await saveProfile(testProfile);
        addedProfiles.push(testProfile.name);
      }
    }
    
    // Si des profiles ont été ajoutés, informer l'utilisateur
    if (addedProfiles.length > 0) {
      toast({
        title: 'Profiles de test ajoutés',
        description: `${addedProfiles.join(', ')} ont été créés. Configurez vos clés API pour tester.`,
        duration: 5000,
      });
    }
    
    // Rafraîchir les profiles après ajout
    const { profiles: updatedProfiles } = useSettingsStore.getState();
    return updatedProfiles;
  };

  const handleToggle = async (providerId: string, enabled: boolean) => {
    try {
      console.log(`[Toggle] Starting toggle for provider: ${providerId}, enabled: ${enabled}`);
      
      // Set manual toggle flag to prevent auto-sync conflicts
      setIsManualToggle(true);
      
      // Get the current provider configuration
      const currentConfig = await ProviderService.getUserProviderConfig(providerId) || {};
      
      // Update the enabled status in the configuration
      const updatedConfig = {
        ...currentConfig,
        enabled: enabled,
        lastUpdated: new Date().toISOString()
      };
      
      console.log(`[Toggle] Saving config for ${providerId}:`, updatedConfig);
      
      // Save the updated configuration
      await ProviderService.saveUserProviderConfig(providerId, updatedConfig);
      
      // Update the local providers state to reflect the change
      setProvidersState((prevProviders: Provider[]) => 
        prevProviders.map((provider: Provider) => 
          provider.id === providerId 
            ? { ...provider, isWorking: enabled ? true : false }
            : provider
        )
      );
      
      console.log(`[Toggle] Updated local state for ${providerId}`);
      
      // Sync with auto-switching (manual operation)
      await syncProviderWithAutoSwitching(providerId, 'toggle', enabled);
      
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
    } finally {
      // Reset manual toggle flag after a short delay
      setTimeout(() => setIsManualToggle(false), 500);
    }
  };

  const handleRemove = (providerId: string) => {
    // Pour l'instant, on ne fait rien car on utilise les profiles
    // Remove provider
  };

  const handleRefresh = () => {
    window.location.reload();
  };

  if (isLoading) {
    return (
      <SettingsSection
        title={t('accounts.multiConnector.title')}
        description={t('accounts.multiConnector.description')}
      >
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          <span className="text-sm text-gray-600">Chargement des providers...</span>
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
      title={t('accounts.multiConnector.title')}
      description={t('accounts.multiConnector.description')}
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

          {providersState.filter(p => p.isWorking === false).length > 0 && (
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
            />
          </div>

          {/* Auto-switching settings - tiroir compact */}
          <div className={`${autoSwitchingOpen ? "flex-1" : "w-auto"} transition-all duration-300`}>
            {!autoSwitchingOpen ? (
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
            ) : (
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
            )}
          </div>
        </div>
      </div>

      {/* Sheet de configuration - tiroir ouvrant sur la droite */}
      <Sheet open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
        <SheetContent side="right" className="w-[95vw] max-w-[1200px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>
              {t('sections.accounts.providerConfig.title')} {selectedProvider?.name}
            </SheetTitle>
          </SheetHeader>
          <div className="mt-6">
            <ProviderConfigDialog
              isOpen={configDialogOpen}
              onOpenChange={setConfigDialogOpen}
              provider={selectedProvider}
              settings={settings}
              onSettingsChange={onSettingsChange}
              onTest={handleTest}
              useSheet={true}
            />
          </div>
        </SheetContent>
      </Sheet>
    </SettingsSection>
  );
}
