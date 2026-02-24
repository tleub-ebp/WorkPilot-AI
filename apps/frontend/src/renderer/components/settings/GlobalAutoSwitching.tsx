import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Switch } from '../ui/switch';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { Loader2, RefreshCw, Activity, AlertCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { AccountPriorityList, type UnifiedAccount } from './AccountPriorityList';
import { useSettingsStore, saveSettings } from '../../stores/settings-store';
import { useClaudeProfileStore, loadClaudeProfiles as loadGlobalClaudeProfiles } from '../../stores/claude-profile-store';
import type { AppSettings } from '../../../shared/types';

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
      console.log('[GlobalAutoSwitching] Starting provider detection...');
      const providers: AuthenticatedProvider[] = [];

      // Check Copilot via GitHub CLI
      try {
        console.log('[GlobalAutoSwitching] Checking Copilot auth...');
        if (!window.electronAPI || !window.electronAPI.checkCopilotAuth) {
          console.error('[GlobalAutoSwitching] window.electronAPI.checkCopilotAuth is not available');
          return;
        }
        
        const copilotResult = await window.electronAPI.checkCopilotAuth();
        console.log('[GlobalAutoSwitching] Copilot result:', copilotResult);
        
        if (copilotResult && copilotResult.success && copilotResult.data?.authenticated) {
          const copilotProvider = {
            id: 'copilot', // Use same ID as CleanProviderSection
            name: 'copilot',
            label: 'GitHub Copilot',
            isAuthenticated: true,
            username: copilotResult.data.username,
          };
          providers.push(copilotProvider);
          console.log('[GlobalAutoSwitching] Added Copilot provider:', copilotProvider);
        } else {
          console.log('[GlobalAutoSwitching] Copilot not authenticated or result invalid');
        }
      } catch (err) {
        console.error('[GlobalAutoSwitching] Failed to check Copilot auth:', err);
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
          console.log(`[GlobalAutoSwitching] Added API key provider: ${name}`, provider);
        }
      });

      console.log('[GlobalAutoSwitching] Final detected providers:', providers);
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
    console.log('[GlobalAutoSwitching] Building unified accounts...');
    console.log('[GlobalAutoSwitching] Authenticated providers:', authenticatedProviders);
    console.log('[GlobalAutoSwitching] Priority order:', priorityOrder);
    
    const unifiedList: UnifiedAccount[] = [];
    
    // Add OAuth profiles with usage data
    claudeProfiles.forEach((profile) => {
      const usageData = profileUsageData.get(profile.id);
      unifiedList.push({
        id: `oauth-${profile.id}`,
        name: profile.name,
        type: 'oauth',
        displayName: profile.name,
        identifier: profile.email || t('accounts.priority.noEmail'),
        isActive: profile.id === activeClaudeProfileId && !activeApiProfileId,
        isNext: false,
        isAvailable: profile.isAuthenticated ?? false,
        hasUnlimitedUsage: false,
        // Use real usage data from the usage monitor
        sessionPercent: usageData?.sessionPercent,
        weeklyPercent: usageData?.weeklyPercent,
        isRateLimited: usageData?.isRateLimited,
        rateLimitType: usageData?.rateLimitType,
        isAuthenticated: profile.isAuthenticated,
        needsReauthentication: usageData?.needsReauthentication,
      });
    });
    
    // Add API profiles
    apiProfiles.forEach((profile) => {
      console.log(`[GlobalAutoSwitching] Processing API profile: ${profile.name} (ID: ${profile.id})`);
      
      // Only add if profile is in priority order or if priority order is empty (backward compatibility)
      const profileName = profile.name.toLowerCase().replace(/\s+/g, '-');
      
      // Check if profile name matches any provider in priority order
      const isInPriorityOrder = priorityOrder.length === 0 || priorityOrder.some(providerId => {
        // Handle different matching strategies
        if (providerId === profileName) return true; // Exact match
        if (profile.name.toLowerCase().includes(providerId)) return true; // Profile name contains provider ID
        if (providerId === 'openai' && profile.name.toLowerCase().includes('openai')) return true;
        if (providerId === 'google' && profile.name.toLowerCase().includes('google')) return true;
        if (providerId === 'anthropic' && profile.name.toLowerCase().includes('anthropic')) return true;
        if (providerId === 'mistral' && profile.name.toLowerCase().includes('mistral')) return true;
        return false;
      });
      
      console.log(`[GlobalAutoSwitching] Profile ${profile.name} - in priority order: ${isInPriorityOrder}`);
      
      if (isInPriorityOrder) {
        unifiedList.push({
          id: `api-${profile.id}`,
          name: profile.name,
          type: 'api',
          displayName: profile.name,
          identifier: profile.baseUrl,
          isActive: profile.id === activeApiProfileId,
          isNext: false,
          isAvailable: true,
          hasUnlimitedUsage: true,
          sessionPercent: undefined,
          weeklyPercent: undefined,
        });
        console.log(`[GlobalAutoSwitching] Added profile ${profile.name} to unified list`);
      }
    });

    // Add authenticated providers (Copilot, OpenAI, etc.) - only if they are in priority order or if no priority order is set
    authenticatedProviders.forEach((prov) => {
      console.log(`[GlobalAutoSwitching] Processing provider: ${prov.name}, id: ${prov.id}`);
      
      // Skip if already represented by an API profile
      const alreadyInList = unifiedList.some((a) => a.name === prov.name || a.id === prov.id);
      console.log(`[GlobalAutoSwitching] ${prov.name} already in list: ${alreadyInList}`);
      
      // Show provider if it's in priority order OR if priority order is empty (backward compatibility)
      // But only show authenticated providers when priority order is empty if they are actually configured
      const isInPriorityOrder = priorityOrder.includes(prov.id);
      const showWhenEmpty = priorityOrder.length === 0 && (
        prov.name === 'copilot' && prov.isAuthenticated // Always show authenticated Copilot when no priority order
      );
      
      console.log(`[GlobalAutoSwitching] ${prov.name} - in priority order: ${isInPriorityOrder}, show when empty: ${showWhenEmpty}`);
      
      if (!alreadyInList && (isInPriorityOrder || showWhenEmpty)) {
        const account = {
          id: prov.id,
          name: prov.name,
          type: 'api' as const,
          displayName: prov.label,
          identifier: prov.username ? `@${prov.username}` : t('accounts.priority.providerAuth'),
          isActive: false,
          isNext: false,
          isAvailable: true,
          hasUnlimitedUsage: prov.name !== 'copilot',
          sessionPercent: undefined,
          weeklyPercent: undefined,
          isAuthenticated: true,
        };
        unifiedList.push(account);
        console.log(`[GlobalAutoSwitching] Added ${prov.name} to unified list:`, account);
      }
    });

    console.log('[GlobalAutoSwitching] Unified list before sorting:', unifiedList);

    // Sort by priority order if available
    if (priorityOrder.length > 0) {
      unifiedList.sort((a, b) => {
        const aIndex = priorityOrder.indexOf(a.id);
        const bIndex = priorityOrder.indexOf(b.id);
        const aPos = aIndex === -1 ? Infinity : aIndex;
        const bPos = bIndex === -1 ? Infinity : bIndex;
        return aPos - bPos;
      });
    }

    console.log('[GlobalAutoSwitching] Final unified list:', unifiedList);
    return unifiedList;
  };

  const unifiedAccounts = buildUnifiedAccounts();

  // Sync priority order with settings.providerPriorityOrder
  useEffect(() => {
    if (settings.providerPriorityOrder && settings.providerPriorityOrder.length > 0) {
      setPriorityOrder(settings.providerPriorityOrder);
    }
  }, [settings.providerPriorityOrder]);

  // Load priority order from settings
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
      // Save to Electron API
      await window.electronAPI.setAccountPriorityOrder(newOrder);
      
      // Also save to settings for consistency
      onSettingsChange({
        ...settings,
        providerPriorityOrder: newOrder
      });
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
