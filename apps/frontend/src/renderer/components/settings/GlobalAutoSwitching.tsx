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

  // Detect authenticated providers on mount and when settings change
  useEffect(() => {
    const detectAuthenticatedProviders = async () => {
      const providers: AuthenticatedProvider[] = [];

      // Check Copilot via GitHub CLI
      try {
        const copilotResult = await window.electronAPI.checkCopilotAuth();
        if (copilotResult.success && copilotResult.data?.authenticated) {
          providers.push({
            id: 'provider-copilot',
            name: 'copilot',
            label: 'GitHub Copilot',
            isAuthenticated: true,
            username: copilotResult.data.username,
          });
        }
      } catch (err) {
        console.warn('[GlobalAutoSwitching] Failed to check Copilot auth:', err);
      }

      // Check API-key based providers from settings
      const apiKeyProviders: Array<{ name: string; label: string; key: keyof AppSettings }> = [
        { name: 'openai', label: 'OpenAI', key: 'globalOpenAIApiKey' },
        { name: 'google', label: 'Google (Gemini)', key: 'globalGoogleDeepMindApiKey' },
        { name: 'mistral', label: 'Mistral AI', key: 'globalMistralApiKey' },
        { name: 'grok', label: 'Grok (xAI)', key: 'globalGrokApiKey' },
        { name: 'deepseek', label: 'DeepSeek', key: 'globalDeepSeekApiKey' },
        { name: 'aws', label: 'AWS (Bedrock)', key: 'globalAWSApiKey' },
      ];

      for (const prov of apiKeyProviders) {
        const apiKey = settings[prov.key];
        if (apiKey && typeof apiKey === 'string' && apiKey.trim().length > 0) {
          providers.push({
            id: `provider-${prov.name}`,
            name: prov.name,
            label: prov.label,
            isAuthenticated: true,
          });
        }
      }

      setAuthenticatedProviders(providers);
    };

    if (isOpen) {
      detectAuthenticatedProviders();
    }
  }, [isOpen, settings]);

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
    });

    // Add authenticated providers (Copilot, OpenAI, etc.)
    authenticatedProviders.forEach((prov) => {
      // Skip if already represented by an API profile
      const alreadyInList = unifiedList.some((a) => a.name === prov.name || a.id === prov.id);
      if (!alreadyInList) {
        unifiedList.push({
          id: prov.id,
          name: prov.name,
          type: 'api',
          displayName: prov.label,
          identifier: prov.username ? `@${prov.username}` : t('accounts.priority.providerAuth'),
          isActive: false,
          isNext: false,
          isAvailable: true,
          hasUnlimitedUsage: prov.name !== 'copilot',
          sessionPercent: undefined,
          weeklyPercent: undefined,
          isAuthenticated: true,
        });
      }
    });

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

    return unifiedList;
  };

  const unifiedAccounts = buildUnifiedAccounts();

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
            <p className="text-xs text-muted-foreground">
              {t('settings:autoSwitching.priorityOrder.description')}
            </p>
            {/* Debug: Afficher le nombre de comptes */}
            <div className="text-xs text-muted-foreground bg-muted/50 p-2 rounded">
              {t('settings:autoSwitching.debug.accountsFound', { count: unifiedAccounts.length })}
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
