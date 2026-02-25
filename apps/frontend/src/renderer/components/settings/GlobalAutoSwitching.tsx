import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Switch } from '../ui/switch';
import { Label } from '../ui/label';
import { RefreshCw, Activity, AlertCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { AccountPriorityList, type UnifiedAccount } from './AccountPriorityList';
import { useSettingsStore, saveSettings } from '../../stores/settings-store';
import { useClaudeProfileStore, loadClaudeProfiles as loadGlobalClaudeProfiles } from '../../stores/claude-profile-store';
import type { AppSettings } from '../../../shared/types';
import { getStaticProviders } from '@shared/utils/providers';
import { getProvider as getRegistryProvider } from '@shared/services/providerRegistry';

/** Authenticated provider entry for the priority list */
interface AuthenticatedProvider {
  id: string;
  name: string;
  label: string;
  isAuthenticated: boolean;
  username?: string;
}

interface GlobalAutoSwitchingProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
  isOpen: boolean;
  useSheet?: boolean;
}

export function GlobalAutoSwitching({ settings, onSettingsChange, isOpen, useSheet = false }: GlobalAutoSwitchingProps) {
  const { t } = useTranslation('settings');
  const { toast } = useToast();
  const { profiles: apiProfiles, activeProfileId: activeApiProfileId } = useSettingsStore();
  const { profiles: claudeProfiles, activeProfileId: activeClaudeProfileId } = useClaudeProfileStore();
  const [isLoading, setIsLoading] = useState(false);
  
  // Priority order state
  const [priorityOrder, setPriorityOrder] = useState<string[]>([]);
  const [isSavingPriority, setIsSavingPriority] = useState(false);
  const [profileUsageData, setProfileUsageData] = useState<Map<string, any>>(new Map());

  // Authenticated providers (Copilot, OpenAI, etc.)
  const [authenticatedProviders, setAuthenticatedProviders] = useState<AuthenticatedProvider[]>([]);
  
  // Auto-switching state - initialize from settings
  const [autoSwitchEnabled, setAutoSwitchEnabled] = useState(settings.autoSwitchEnabled ?? false);
  const [proactiveEnabled, setProactiveEnabled] = useState(settings.proactiveEnabled ?? true);
  const [sessionThreshold, setSessionThreshold] = useState(settings.sessionThreshold ?? 95);
  const [rateLimitEnabled, setRateLimitEnabled] = useState(settings.rateLimitEnabled ?? false);
  const [authFailureEnabled, setAuthFailureEnabled] = useState(settings.authFailureEnabled ?? false);

  // Load Claude profiles on mount
  useEffect(() => {
    loadGlobalClaudeProfiles();
  }, []);

  // Detect authenticated providers on mount and when relevant settings change
  useEffect(() => {
    const detectAuthenticatedProviders = async () => {
      const providers: AuthenticatedProvider[] = [];

      // Check Copilot via GitHub CLI
      try {
        if (!window.electronAPI || !window.electronAPI.checkCopilotAuth) {
          return;
        }
        
        const copilotResult = await window.electronAPI.checkCopilotAuth();
        
        if (copilotResult && copilotResult.success && copilotResult.data?.authenticated) {
          const copilotProvider = {
            id: 'copilot', // Use same ID as CleanProviderSection
            name: 'copilot',
            label: 'GitHub Copilot',
            isAuthenticated: true,
            username: copilotResult.data.username,
          };
          providers.push(copilotProvider);
        }
      } catch (err) {
        console.error('[GlobalAutoSwitching] Error details:', err instanceof Error ? err.message : String(err));
      }

      // Check API-key based providers from settings
      const apiKeyProviders = [
        { name: 'openai', label: 'OpenAI', key: 'globalOpenAIApiKey' },
        { name: 'google', label: 'Google (Gemini)', key: 'globalGoogleDeepMindApiKey' },
        { name: 'mistral', label: 'Mistral AI', key: 'globalMistralApiKey' },
        { name: 'grok', label: 'Grok (xAI)', key: 'globalGrokApiKey' },
        { name: 'deepseek', label: 'DeepSeek', key: 'globalDeepSeekApiKey' },
        { name: 'aws', label: 'AWS (Bedrock)', key: 'globalAWSApiKey' },
        { name: 'meta', label: 'Meta AI', key: 'globalMetaApiKey' },
        { name: 'azure-openai', label: 'Azure OpenAI', key: 'globalOpenAIApiKey' },
      ];

      apiKeyProviders.forEach(({ name, label, key }) => {
        if (settings[key as keyof AppSettings]) {
          const provider = {
            id: name, // Use same ID as CleanProviderSection (without 'provider-' prefix)
            name,
            label,
            isAuthenticated: true,
          };
          providers.push(provider);
        }
      });

      setAuthenticatedProviders(providers);
    };

    if (isOpen) {
      detectAuthenticatedProviders();
    }
  }, [isOpen, 
    settings.globalOpenAIApiKey, 
    settings.globalGoogleDeepMindApiKey, 
    settings.globalMistralApiKey, 
    settings.globalGrokApiKey, 
    settings.globalDeepSeekApiKey, 
    settings.globalAWSApiKey, 
    settings.globalMetaApiKey
  ]);

  // Sync autoSwitchEnabled with settings
  useEffect(() => {
    setAutoSwitchEnabled(settings.autoSwitchEnabled ?? false);
  }, [settings.autoSwitchEnabled]);

  // Sync other auto-switching settings with settings
  useEffect(() => {
    setProactiveEnabled(settings.proactiveEnabled ?? true);
    setSessionThreshold(settings.sessionThreshold ?? 95);
    setRateLimitEnabled(settings.rateLimitEnabled ?? false);
    setAuthFailureEnabled(settings.authFailureEnabled ?? false);
  }, [settings.proactiveEnabled, settings.sessionThreshold, settings.rateLimitEnabled, settings.authFailureEnabled]);

  // Build unified accounts list
  const buildUnifiedAccounts = (): UnifiedAccount[] => {
    const unifiedList: UnifiedAccount[] = [];

    // Track which providers are already represented to avoid duplicates
    const representedProviders = new Set<string>();

    // Helper: get display label from providerRegistry for consistent naming with left grid
    const getRegistryLabel = (providerName: string): string => {
      const regProvider = getRegistryProvider(providerName);
      return regProvider?.label || providerName;
    };

    // Helper: detect provider name from an API profile (URL + name based)
    const detectProviderFromProfile = (profile: { baseUrl?: string; name?: string }): string => {
      const url = profile.baseUrl?.toLowerCase() || '';
      const name = profile.name?.toLowerCase() || '';

      if (url.includes('anthropic.com') || name.includes('claude') || name.includes('anthropic')) return 'anthropic';
      if (url.includes('openai.com') || name.includes('openai') || name.includes('chatgpt')) return 'openai';
      if (url.includes('google.com') || name.includes('gemini') || name.includes('google')) return 'google';
      if (url.includes('mistral.ai') || name.includes('mistral')) return 'mistral';
      if (url.includes('deepseek.com') || name.includes('deepseek')) return 'deepseek';
      if (url.includes('meta.com') || name.includes('llama') || name.includes('meta')) return 'meta';
      if (url.includes('x.ai') || name.includes('grok')) return 'grok';
      if (url.includes('aws.amazon.com') || name.includes('bedrock') || name.includes('aws')) return 'aws';
      if (url.includes('ollama') || name.includes('ollama') || url.includes('localhost') || url.includes('127.0.0.1')) return 'ollama';
      if (url.includes('github.com') || name.includes('copilot')) return 'copilot';

      return 'custom';
    };

    // Loop 1: Add OAuth profiles (Claude accounts) with usage data
    claudeProfiles.forEach((profile) => {
      const usageData = profileUsageData.get(profile.id);
      unifiedList.push({
        id: `oauth-${profile.id}`,
        name: 'anthropic',
        type: 'oauth',
        displayName: getRegistryLabel('anthropic'),
        identifier: profile.email || profile.name || t('accounts.priority.noEmail'),
        isActive: profile.id === activeClaudeProfileId && !activeApiProfileId,
        isNext: false,
        isAvailable: profile.isAuthenticated ?? false,
        hasUnlimitedUsage: false,
        sessionPercent: usageData?.sessionPercent,
        weeklyPercent: usageData?.weeklyPercent,
        isRateLimited: usageData?.isRateLimited,
        rateLimitType: usageData?.rateLimitType,
        isAuthenticated: profile.isAuthenticated,
        needsReauthentication: usageData?.needsReauthentication,
      });
      representedProviders.add('anthropic');
    });
    
    // Loop 2: Add ALL API profiles (no priority order filter — show all configured profiles)
    apiProfiles.forEach((profile) => {
      const providerName = detectProviderFromProfile(profile);

      // Skip Anthropic profiles since they are already covered by OAuth (Loop 1)
      if (providerName === 'anthropic' && representedProviders.has('anthropic')) return;

      unifiedList.push({
        id: `api-${profile.id}`,
        name: providerName,
        type: 'api',
        displayName: getRegistryLabel(providerName),
        identifier: profile.baseUrl || profile.name,
        isActive: profile.id === activeApiProfileId,
        isNext: false,
        isAvailable: true,
        hasUnlimitedUsage: true,
        sessionPercent: undefined,
        weeklyPercent: undefined,
      });
      representedProviders.add(providerName);
    });

    // Loop 3: Add authenticated providers (Copilot, settings-based API keys)
    // Only if not already represented by OAuth or API profiles
    authenticatedProviders.forEach((prov) => {
      if (representedProviders.has(prov.name)) return;

      unifiedList.push({
        id: prov.id,
        name: prov.name,
        type: 'api' as const,
        displayName: getRegistryLabel(prov.name),
        identifier: prov.username ? `@${prov.username}` : t('accounts.priority.providerAuth'),
        isActive: false,
        isNext: false,
        isAvailable: true,
        hasUnlimitedUsage: prov.name !== 'copilot',
        sessionPercent: undefined,
        weeklyPercent: undefined,
        isAuthenticated: true,
      });
      representedProviders.add(prov.name);
    });

    // Fallback: use getStaticProviders() to catch any configured providers not yet represented
    // This ensures profiles detected by URL/name matching appear even if Loops 2 & 3 missed them
    const { providers: staticProviders, status: staticStatus } = getStaticProviders(apiProfiles);
    for (const sp of staticProviders) {
      if (representedProviders.has(sp.name)) continue;
      if (!staticStatus[sp.name]) continue; // Not configured/authenticated

      unifiedList.push({
        id: sp.name,
        name: sp.name,
        type: 'api' as const,
        displayName: getRegistryLabel(sp.name),
        identifier: t('accounts.priority.providerAuth'),
        isActive: false,
        isNext: false,
        isAvailable: true,
        hasUnlimitedUsage: sp.name !== 'copilot',
        sessionPercent: undefined,
        weeklyPercent: undefined,
        isAuthenticated: true,
      });
      representedProviders.add(sp.name);
    }

    // Filter out providers explicitly disabled by the user toggle
    const disabledProviders: string[] = (settings as any).disabledAutoSwitchProviders || [];
    const filteredList = disabledProviders.length > 0
      ? unifiedList.filter(account => !disabledProviders.includes(account.id) && !disabledProviders.includes(account.name))
      : unifiedList;

    // Sort by priority order if available, with improved matching by id or provider name
    if (priorityOrder.length > 0) {
      filteredList.sort((a, b) => {
        const findIndex = (account: UnifiedAccount): number => {
          let idx = priorityOrder.indexOf(account.id);
          if (idx !== -1) return idx;
          idx = priorityOrder.indexOf(account.name);
          if (idx !== -1) return idx;
          return -1;
        };
        const aPos = findIndex(a) === -1 ? Infinity : findIndex(a);
        const bPos = findIndex(b) === -1 ? Infinity : findIndex(b);
        return aPos - bPos;
      });
    }
    return filteredList;
  };

  const unifiedAccounts = buildUnifiedAccounts();

  // Load priority order from ClaudeProfileManager
  const loadPriorityOrder = async () => {
    try {
      const result = await window.electronAPI.getAccountPriorityOrder();
      if (result.success && result.data) {
        setPriorityOrder(result.data);
      }
    } catch (err) {
      console.warn('[GlobalAutoSwitching] Failed to load priority order:', err);
    }
  };

  // Save priority order
  const handlePriorityReorder = async (newOrder: string[]) => {
    setPriorityOrder(newOrder);
    setIsSavingPriority(true);
    try {
      // Save to ClaudeProfileManager (single source of truth)
      await window.electronAPI.setAccountPriorityOrder(newOrder);
    } catch (err) {
      console.warn('[GlobalAutoSwitching] Failed to save priority order:', err);
      toast({
        variant: 'destructive',
        title: t('autoSwitching.toast.error'),
        description: t('autoSwitching.toast.errorDescription'),
      });
    } finally {
      setIsSavingPriority(false);
    }
  };

  // Load data when section is opened
  useEffect(() => {
    if (isOpen) {
      loadPriorityOrder();
      // Also refresh Claude profiles when opening
      loadGlobalClaudeProfiles();
    }
  }, [isOpen]);

  const handleToggleAutoSwitch = async (enabled: boolean) => {
    // Update local state immediately for better UX
    setAutoSwitchEnabled(enabled);
    
    setIsLoading(true);
    try {
      // Save to settings
      const success = await saveSettings({ autoSwitchEnabled: enabled });
      
      if (success) {
        // Also propagate to parent
        onSettingsChange({
          ...settings,
          autoSwitchEnabled: enabled
        });
        
        toast({
          title: enabled ? t('settings:autoSwitching.enabled') : t('settings:autoSwitching.disabled'),
          description: enabled ? t('settings:autoSwitching.enabledDescription') : t('settings:autoSwitching.disabledDescription'),
        });
      } else {
        // Revert state if save failed
        setAutoSwitchEnabled(!enabled);
        throw new Error('Failed to save settings');
      }
    } catch (error) {
      // Revert state if save failed
      setAutoSwitchEnabled(!enabled);
      toast({
        variant: 'destructive',
        title: t('settings:autoSwitching.toast.error'),
        description: t('settings:autoSwitching.toast.errorDescription'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateSetting = async (updates: any) => {
    setIsLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Mettre à jour les états locaux
      if (updates.proactiveEnabled !== undefined) setProactiveEnabled(updates.proactiveEnabled);
      if (updates.sessionThreshold !== undefined) setSessionThreshold(updates.sessionThreshold);
      if (updates.rateLimitEnabled !== undefined) setRateLimitEnabled(updates.rateLimitEnabled);
      if (updates.authFailureEnabled !== undefined) setAuthFailureEnabled(updates.authFailureEnabled);
      
      // Save to global settings
      const success = await saveSettings(updates);
      
      if (success) {
        // Also propagate to parent
        onSettingsChange({
          ...settings,
          ...updates
        });
      } else {
        throw new Error('Failed to save settings');
      }
      
    } catch (error) {
      toast({
        variant: 'destructive',
        title: t('settings:autoSwitching.toast.error'),
        description: t('settings:autoSwitching.toast.errorDescription'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Master toggle */}
      <div className="flex items-center justify-between">
        <div>
          <Label className="text-sm font-medium">{t('settings:autoSwitching.enableLabel')}</Label>
          <p className="text-xs text-muted-foreground mt-1">
            {t('settings:autoSwitching.enableDescription')}
          </p>
        </div>
        <Switch
          checked={autoSwitchEnabled}
          onCheckedChange={handleToggleAutoSwitch}
          disabled={isLoading}
        />
      </div>

      {autoSwitchEnabled && (
        <>
          {/* Proactive Monitoring */}
          <div className="pl-6 space-y-4 pt-2 border-l-2 border-primary/20">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm font-medium flex items-center gap-2">
                  <Activity className="h-3.5 w-3.5" />
                  {t('settings:autoSwitching.proactiveMonitoring')}
                </Label>
                <p className="text-xs text-muted-foreground mt-1">
                  {t('settings:autoSwitching.proactiveDescription')}
                </p>
              </div>
              <Switch
                checked={proactiveEnabled}
                onCheckedChange={(value) => handleUpdateSetting({ proactiveEnabled: value })}
                disabled={isLoading}
              />
            </div>

          {/* Session threshold */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="session-threshold" className="text-sm">{t('settings:autoSwitching.sessionThreshold')}</Label>
              <span className="text-sm font-mono">{sessionThreshold}%</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={0}
                max={99}
                step={1}
                value={sessionThreshold}
                onChange={(e) => handleUpdateSetting({ sessionThreshold: parseInt(e.target.value, 10) })}
                disabled={isLoading}
                className="flex-1"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {t('settings:autoSwitching.sessionThresholdDescription')}
            </p>
          </div>

          {/* Rate limit switching */}
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-sm font-medium flex items-center gap-2">
                <AlertCircle className="h-3.5 w-3.5" />
                {t('settings:autoSwitching.rateLimitSwitching')}
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                {t('settings:autoSwitching.rateLimitDescription')}
              </p>
            </div>
            <Switch
              checked={rateLimitEnabled}
              onCheckedChange={(value) => handleUpdateSetting({ rateLimitEnabled: value })}
              disabled={isLoading}
            />
          </div>

          {/* Auth failure switching */}
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-sm font-medium">
                {t('settings:autoSwitching.authFailureSwitching')}
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                {t('settings:autoSwitching.authFailureDescription')}
              </p>
            </div>
            <Switch
              checked={authFailureEnabled}
              onCheckedChange={(value) => handleUpdateSetting({ authFailureEnabled: value })}
              disabled={isLoading}
            />
          </div>
        </>
      )}

      {/* Account Priority Order */}
      {autoSwitchEnabled && unifiedAccounts.length > 0 && (
        <div className="pt-4 border-t border-border/50">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
              <h4 className="text-sm font-medium text-foreground">
                {t('settings:autoSwitching.priorityOrder.title')}
              </h4>
            </div>
            
            <AccountPriorityList
              accounts={unifiedAccounts}
              onReorder={handlePriorityReorder}
              isLoading={isSavingPriority}
            />
          </div>
        </div>
      )}
    </div>
  );
}
