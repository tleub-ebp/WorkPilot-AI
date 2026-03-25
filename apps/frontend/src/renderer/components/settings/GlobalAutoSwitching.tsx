import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Switch } from '../ui/switch';
import { Label } from '../ui/label';
import { RefreshCw, Activity, AlertCircle, Zap, ArrowDownUp, BarChart3, Router } from 'lucide-react';
import { cn } from '@/lib/utils';
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
  readonly settings: AppSettings;
  readonly onSettingsChange: (settings: AppSettings) => void;
  readonly isOpen: boolean;
  /** Pre-computed provider status from the parent grid (includes OAuth enrichment).
   *  When provided, used as the source of truth to filter providers — guarantees
   *  the priority list is ISO with what the grid shows. */
  readonly providerStatus?: Record<string, boolean>;
}

export function GlobalAutoSwitching({ settings, onSettingsChange, isOpen, providerStatus }: GlobalAutoSwitchingProps) {
  const { t } = useTranslation('settings');
  const { toast } = useToast();
  const { profiles: apiProfiles, activeProfileId: activeApiProfileId } = useSettingsStore();
  const { profiles: claudeProfiles, activeProfileId: activeClaudeProfileId } = useClaudeProfileStore();
  const [isLoading, setIsLoading] = useState(false);
  
  // Priority order state
  const [priorityOrder, setPriorityOrder] = useState<string[]>([]);
  const [isSavingPriority, setIsSavingPriority] = useState(false);
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  const [profileUsageData] = useState<Map<string, any>>(new Map());

  // Authenticated providers (Copilot, OpenAI, etc.)
  const [authenticatedProviders, setAuthenticatedProviders] = useState<AuthenticatedProvider[]>([]);
  
  // Unified accounts state
  const [unifiedAccounts, setUnifiedAccounts] = useState<UnifiedAccount[]>([]);
  
  // Auto-switching state - initialize from settings
  const [autoSwitchEnabled, setAutoSwitchEnabled] = useState(settings.autoSwitchEnabled ?? false);
  const [proactiveEnabled, setProactiveEnabled] = useState(settings.proactiveEnabled ?? true);
  const [sessionThreshold, setSessionThreshold] = useState(settings.sessionThreshold ?? 95);
  const [rateLimitEnabled, setRateLimitEnabled] = useState(settings.rateLimitEnabled ?? false);
  const [authFailureEnabled, setAuthFailureEnabled] = useState(settings.authFailureEnabled ?? false);
  const [routingStrategy, setRoutingStrategy] = useState(settings.routingStrategy ?? 'best_performance');

  // Load Claude profiles on mount
  useEffect(() => {
    loadGlobalClaudeProfiles();
  }, []);

  // Detect authenticated providers on mount and when relevant settings change
  // biome-ignore lint/correctness/useExhaustiveDependencies: intentional dependency omission
  useEffect(() => {
    const detectAuthenticatedProviders = async () => {
      const providers: AuthenticatedProvider[] = [];

      // Check Copilot via GitHub CLI
      try {
        if (!globalThis.electronAPI?.checkCopilotAuth) {
          return;
        }
        
        const copilotResult = await globalThis.electronAPI.checkCopilotAuth();
        
        if (copilotResult?.success && copilotResult.data?.authenticated) {
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
    settings.globalMetaApiKey,
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
    setRoutingStrategy(settings.routingStrategy ?? 'best_performance');
  }, [settings.proactiveEnabled, settings.sessionThreshold, settings.rateLimitEnabled, settings.authFailureEnabled, settings.routingStrategy]);

  // Build unified accounts list — getStaticProviders is the single source of truth,
  // same as the provider grid, to guarantee ISO between the two views.
  const buildUnifiedAccounts = async (): Promise<UnifiedAccount[]> => {
    const unifiedList: UnifiedAccount[] = [];
    const representedProviders = new Set<string>();

    const getRegistryLabel = (providerName: string): string => {
      const regProvider = getRegistryProvider(providerName);
      return regProvider?.label || providerName;
    };

    // Step 1: OAuth Claude profiles → always displayed as "Anthropic (Claude)"
    claudeProfiles.forEach((profile) => {
      const usageData = profileUsageData.get(profile.id);
      unifiedList.push({
        id: `oauth-${profile.id}`,
        name: profile.name,
        type: 'oauth',
        displayName: getRegistryLabel('anthropic'), // "Anthropic (Claude)" — not the account nickname
        identifier: profile.email || t('accounts.priority.noEmail'),
        isActive: profile.id === activeClaudeProfileId && !activeApiProfileId,
        isNext: false,
        isAvailable: profile.isAuthenticated ?? false,
        hasUnlimitedUsage: false,
        sessionPercent: usageData?.sessionPercent,
        weeklyPercent: usageData?.weeklyPercent,
      });
      representedProviders.add(profile.name);
      representedProviders.add('anthropic'); // block duplicate API Anthropic entry
    });

    // Step 2: All other providers via getStaticProviders — same source as the provider grid
    // Use parent's providerStatus when available (already OAuth-enriched, matches the grid exactly).
    // Fall back to getStaticProviders for standalone usage (e.g. outside CleanProviderSection).
    const { providers: staticProviders, status: fallbackStatus } = await getStaticProviders(apiProfiles, settings);
    const effectiveStatus = providerStatus ?? fallbackStatus;

    // Copilot username (from async auth check) for a nicer identifier
    const copilotProvider = authenticatedProviders.find((p) => p.name === 'copilot');
    // Matching API profile for URL-based identifier
    const findApiProfile = (providerName: string) =>
      apiProfiles.find((p) => {
        const url = p.baseUrl?.toLowerCase() || '';
        const n = p.name?.toLowerCase() || '';
        if (providerName === 'openai') return url.includes('openai.com') || n.includes('openai');
        if (providerName === 'google') return url.includes('google.com') || n.includes('gemini');
        if (providerName === 'mistral') return url.includes('mistral.ai') || n.includes('mistral');
        if (providerName === 'deepseek') return url.includes('deepseek.com') || n.includes('deepseek');
        if (providerName === 'grok') return url.includes('x.ai') || n.includes('grok');
        if (providerName === 'windsurf') return url.includes('windsurf') || n.includes('windsurf');
        if (providerName === 'ollama') return url.includes('ollama') || url.includes('localhost');
        return false;
      });

    for (const sp of staticProviders) {
      if (representedProviders.has(sp.name)) continue;
      if (!effectiveStatus[sp.name]) continue; // not configured/authenticated — skip (same filter as grid)

      const matchingProfile = findApiProfile(sp.name);
      const identifier =
        sp.name === 'copilot' && copilotProvider?.username
          ? `@${copilotProvider.username}`
          : matchingProfile?.baseUrl || matchingProfile?.name || t('accounts.priority.providerAuth');

      unifiedList.push({
        id: matchingProfile ? `api-${matchingProfile.id}` : sp.name,
        name: sp.name,
        type: 'api',
        displayName: getRegistryLabel(sp.name),
        identifier,
        isActive: matchingProfile ? matchingProfile.id === activeApiProfileId : false,
        isNext: false,
        isAvailable: true,
        hasUnlimitedUsage: sp.name !== 'copilot',
        sessionPercent: undefined,
        weeklyPercent: undefined,
      });
      representedProviders.add(sp.name);
    }

    const filteredList = unifiedList.filter((account) => account.isAvailable);

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

  // Load unified accounts when dependencies change
  useEffect(() => {
    const loadUnifiedAccounts = async () => {
      const accounts = await buildUnifiedAccounts();
      setUnifiedAccounts(accounts);
    };
    
    loadUnifiedAccounts();
  // biome-ignore lint/correctness/useExhaustiveDependencies: intentional dependency omission
  }, [buildUnifiedAccounts]);

  // Load priority order from ClaudeProfileManager
  const loadPriorityOrder = async () => {
    try {
      const result = await globalThis.electronAPI.getAccountPriorityOrder();
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
      await globalThis.electronAPI.setAccountPriorityOrder(newOrder);
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
  // biome-ignore lint/correctness/useExhaustiveDependencies: intentional dependency omission
  }, [isOpen, loadPriorityOrder]);

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
      console.error('[GlobalAutoSwitching] Failed to toggle auto-switch:', error);
      toast({
        variant: 'destructive',
        title: t('settings:autoSwitching.toast.error'),
        description: t('settings:autoSwitching.toast.errorDescription'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStrategyChange = async (strategy: typeof routingStrategy) => {
    setRoutingStrategy(strategy);
    await handleUpdateSetting({ routingStrategy: strategy });
  };

  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
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
      console.error('[GlobalAutoSwitching] Failed to update settings:', error);
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
          {/* Routing Strategy */}
          <div className="space-y-3">
            <div>
              <Label className="text-sm font-medium flex items-center gap-2">
                <Router className="h-3.5 w-3.5" />
                {t('llmRouter.routingStrategy.title')}
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                {t('llmRouter.routingStrategy.description')}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {([
                { id: 'best_performance', label: t('llmRouter.routingStrategy.bestPerformance'), desc: t('llmRouter.routingStrategy.bestPerformanceDescription'), icon: <Zap className="h-3.5 w-3.5" /> },
                { id: 'cheapest', label: t('llmRouter.routingStrategy.cheapest'), desc: t('llmRouter.routingStrategy.cheapestDescription'), icon: <ArrowDownUp className="h-3.5 w-3.5" /> },
                { id: 'lowest_latency', label: t('llmRouter.routingStrategy.lowestLatency'), desc: t('llmRouter.routingStrategy.lowestLatencyDescription'), icon: <BarChart3 className="h-3.5 w-3.5" /> },
                { id: 'round_robin', label: t('llmRouter.routingStrategy.roundRobin'), desc: t('llmRouter.routingStrategy.roundRobinDescription'), icon: <Router className="h-3.5 w-3.5" /> },
              ] as const).map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => handleStrategyChange(s.id)}
                  disabled={isLoading}
                  className={cn(
                    'flex items-start gap-2 rounded-lg border p-2.5 text-left transition-colors',
                    routingStrategy === s.id
                      ? 'border-primary bg-primary/5 ring-1 ring-primary'
                      : 'border-border hover:bg-accent/50'
                  )}
                >
                  <span className={cn('mt-0.5 shrink-0', routingStrategy === s.id ? 'text-primary' : 'text-muted-foreground')}>{s.icon}</span>
                  <div className="min-w-0">
                    <span className="text-xs font-medium block">{s.label}</span>
                    <p className="text-[10px] text-muted-foreground leading-tight mt-0.5">{s.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

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
                onChange={(e) => handleUpdateSetting({ sessionThreshold: Number.parseInt(e.target.value, 10) })}
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
