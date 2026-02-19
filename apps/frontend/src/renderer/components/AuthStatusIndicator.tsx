/**
 * AuthStatusIndicator - Display a current authentication method in header
 *
 * Shows the active authentication method and provider:
 * - OAuth: Shows "OAuth Anthropic" with Lock icon
 * - API Profile: Shows provider name (Anthropic, OpenAI, Ollama, Copilot) with Key icon and provider-specific colors
 *
 * Provider detection is based on the profile's baseUrl:
 * - api.anthropic.com → Anthropic
 * - github.com/api.github.com → GitHub Copilot
 * - api.openai.com → OpenAI
 * - localhost/127.0.0.1 → Ollama (Local)
 *
 * Usage warning badge: Shows to the left of provider badge when usage exceeds 90%
 */

import { useMemo, useState, useEffect } from 'react';
import { AlertTriangle, Key, Lock, Shield, Server, Fingerprint, ExternalLink } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import { useTranslation } from 'react-i18next';
import { useSettingsStore } from '@/stores/settings-store';
import { detectProvider, getProviderLabel, getProviderBadgeColor, type ApiProvider } from '@shared/utils/provider-detection';
import { formatTimeRemaining, localizeUsageWindowLabel, hasHardcodedText } from '@shared/utils/format-time';
import type { UsageSnapshot } from '@shared/types';
import { useProviderContext } from './ProviderContext';

/**
 * Type-safe mapping from ApiProvider to translation keys
 */
const PROVIDER_TRANSLATION_KEYS: Readonly<Record<ApiProvider, string>> = {
  anthropic: 'common:usage.providerAnthropic',
  openai: 'common:usage.providerOpenAI',
  ollama: 'common:usage.providerOllama',
  ollama_local: 'common:usage.providerOllamaLocal',
  copilot: 'common:usage.providerCopilot',
  unknown: 'common:usage.providerUnknown'
} as const;

/**
 * OAuth fallback state when no profile is active or profile not found
 */
const OAUTH_FALLBACK = {
  type: 'oauth' as const,
  name: 'OAuth',
  provider: 'anthropic' as const,
  providerLabel: 'Anthropic',
  badgeColor: 'bg-orange-500/10 text-orange-500 border-orange-500/20 hover:bg-orange-500/15'
} as const;

export function AuthStatusIndicator() {
  // Subscribe to a profile state from the settings store
  const { profiles, activeProfileId } = useSettingsStore();
  const { t } = useTranslation(['common']);
  const { selectedProvider } = useProviderContext();

  // Track usage data for warning badge
  const [usage, setUsage] = useState<UsageSnapshot | null>(null);
  const [isLoadingUsage, setIsLoadingUsage] = useState(true);

  // Track GitHub CLI status for Copilot provider
  const [githubStatus, setGithubStatus] = useState<{ available: boolean; isAuth?: boolean; username?: string } | null>(null);
  const [isLoadingGithubStatus, setIsLoadingGithubStatus] = useState(false);

  // Single effect: subscribe to live updates + refresh on provider/profile change
  useEffect(() => {
    setIsLoadingUsage(true);
    setUsage(null);

    // Subscribe to live usage push events
    const unsubscribe = window.electronAPI.onUsageUpdated((snapshot: UsageSnapshot) => {
      if (selectedProvider && snapshot.providerName && snapshot.providerName !== selectedProvider) return;
      setUsage(snapshot);
      setIsLoadingUsage(false);
    });

    // Request current usage immediately
    window.electronAPI.requestUsageUpdate()
      .then((result) => {
        if (result.success && result.data) {
          if (selectedProvider && result.data.providerName && result.data.providerName !== selectedProvider) return;
          setUsage(result.data);
        }
      })
      .catch((error) => {
        console.warn('[AuthStatusIndicator] Failed to fetch usage:', error);
      })
      .finally(() => {
        setIsLoadingUsage(false);
      });

    return () => {
      unsubscribe();
    };
  }, [selectedProvider, activeProfileId]);

  // Effect to fetch GitHub CLI status when Copilot provider is selected
  useEffect(() => {
    if (selectedProvider === 'copilot') {
      setIsLoadingGithubStatus(true);
      
      // Request GitHub CLI status from main process
      window.electronAPI.getGithubCliStatus?.()
        .then((result: { success: boolean; data: { available: boolean; isAuth?: boolean; username?: string } }) => {
          if (result.success && result.data) {
            setGithubStatus(result.data);
          } else {
            setGithubStatus({ available: false });
          }
        })
        .catch((error: Error) => {
          console.warn('[AuthStatusIndicator] Failed to fetch GitHub CLI status:', error);
          setGithubStatus({ available: false });
        })
        .finally(() => {
          setIsLoadingGithubStatus(false);
        });
    } else {
      // Clear GitHub status when not using Copilot
      setGithubStatus(null);
      setIsLoadingGithubStatus(false);
    }
  }, [selectedProvider]);

  // Determine if usage warning badge should be shown
  const shouldShowUsageWarning = usage && !isLoadingUsage && (
    usage.sessionPercent >= 90 || usage.weeklyPercent >= 90
  );

  // Get the higher usage percentage for the warning badge
  const warningBadgePercent = usage
    ? Math.max(usage.sessionPercent, usage.weeklyPercent)
    : 0;

  // Get formatted reset times (calculated dynamically from timestamps)
  let sessionResetTime: string | undefined;
  if (usage?.sessionResetTimestamp) {
    const formatted = formatTimeRemaining(usage.sessionResetTimestamp, t);
    sessionResetTime = formatted !== undefined
      ? formatted
      : (!hasHardcodedText(usage?.sessionResetTime) ? usage?.sessionResetTime : undefined);
  } else {
    sessionResetTime = !hasHardcodedText(usage?.sessionResetTime) ? usage?.sessionResetTime : undefined;
  }

  // Calcul dynamique du provider et du profil
  const authStatus = useMemo(() => {
    if (selectedProvider) {
      const providerProfile = profiles.find(p => detectProvider(p.baseUrl) === selectedProvider);
      const provider = selectedProvider as ApiProvider;
      const providerLabel = getProviderLabel(provider);
      if (providerProfile) {
        return {
          type: 'profile',
          name: providerProfile.name,
          id: providerProfile.id,
          baseUrl: providerProfile.baseUrl,
          createdAt: providerProfile.createdAt,
          provider,
          providerLabel,
          badgeColor: getProviderBadgeColor(provider)
        };
      }
      return {
        type: 'provider',
        name: providerLabel,
        provider,
        providerLabel,
        badgeColor: getProviderBadgeColor(provider)
      };
    }
    if (activeProfileId) {
      const activeProfile = profiles.find(p => p.id === activeProfileId);
      if (activeProfile) {
        const provider = detectProvider(activeProfile.baseUrl);
        const providerLabel = getProviderLabel(provider);
        return {
          type: 'profile',
          name: activeProfile.name,
          id: activeProfile.id,
          baseUrl: activeProfile.baseUrl,
          createdAt: activeProfile.createdAt,
          provider,
          providerLabel,
          badgeColor: getProviderBadgeColor(provider)
        };
      }
      return OAUTH_FALLBACK;
    }
    return OAUTH_FALLBACK;
  }, [selectedProvider, profiles, activeProfileId]);

  // Helper function to truncate ID for display
  const truncateId = (id: string | undefined): string => {
    if (!id) return '';
    return id.slice(0, 8);
  };

  // Get localized provider label for display
  // Uses type-safe mapping with fallback to getProviderLabel for unknown providers
  const getLocalizedProviderLabel = (provider: ApiProvider): string => {
    const translationKey = PROVIDER_TRANSLATION_KEYS[provider];

    // If we have a translation key (including providerUnknown), use it
    if (translationKey) {
      const translated = t(translationKey);
      // If translation returns the key itself (not found), use getProviderLabel fallback
      if (translated !== translationKey) {
        return translated;
      }
    }

    // Fallback to getProviderLabel for providers without translation keys
    return getProviderLabel(provider);
  };

  const isOAuth = authStatus.type === 'oauth';
  const Icon = isOAuth ? Lock : Key;
  // Compute once and reuse for aria-label and displayed text
  const localizedProviderLabel = getLocalizedProviderLabel(authStatus.provider);
  // Badge label: nom du provider sélectionné
  const badgeLabel = getProviderLabel(authStatus.provider);

  return (
    <div className="flex items-center gap-2">
      {/* Usage Warning Badge (shown when usage >= 90%) */}
      {shouldShowUsageWarning && (
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-red-500/10 text-red-500 border-red-500/20">
                <AlertTriangle className="h-3.5 w-3.5 motion-safe:animate-pulse" />
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs max-w-xs">
              <div className="space-y-1">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground font-medium">{t('common:usage.usageAlert')}</span>
                  <span className="font-semibold text-red-500">{Math.round(warningBadgePercent)}%</span>
                </div>
                <div className="h-px bg-border" />
                <div className="text-[10px] text-muted-foreground">
                  {t('common:usage.accountExceedsThreshold')}
                </div>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}

      {/* Provider Badge + Popin */}
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border transition-all hover:opacity-80 ${authStatus.badgeColor}`}
              aria-label={t('common:usage.authenticationAriaLabel', { provider: badgeLabel })}
            >
              <Icon className="h-3.5 w-3.5" />
              <span className="text-xs font-semibold">
                {badgeLabel}
              </span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-xs max-w-xs p-0">
            <div className="p-3 space-y-3">
              {/* Header section */}
              <div className="flex items-center justify-between pb-2 border-b">
                <div className="flex items-center gap-1.5">
                  <Shield className="h-3.5 w-3.5" />
                  <span className="font-semibold text-xs">{t('common:usage.authenticationDetails')}</span>
                </div>
                <div className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                  isOAuth
                    ? 'bg-orange-500/15 text-orange-500'
                    : 'bg-primary/15 text-primary'
                }`}>
                  {isOAuth ? t('common:usage.oauth') : t('common:usage.apiKey')}
                </div>
              </div>

              {/* Provider info */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Server className="h-3.5 w-3.5" />
                  <span className="font-medium text-[11px]">{t('common:usage.provider')}</span>
                </div>
                <span className="font-semibold text-xs">{badgeLabel}</span>
              </div>

              {/* Claude Code subscription label for OAuth */}
              {isOAuth && (
                <div className="flex items-center justify-between pt-2 border-t">
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <Lock className="h-3 w-3" />
                    <span className="text-[10px]">{t('common:usage.subscription')}</span>
                  </div>
                  <span className="font-medium text-[10px]">{t('common:usage.claudeCodeSubscription')}</span>
                </div>
              )}

              {/* Profile details for API profiles */}
              {authStatus.type === 'profile' ? (
                <div className="pt-2 border-t space-y-2">
                  {/* Profile name with icon */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Key className="h-3 w-3" />
                      <span className="text-[10px]">{t('common:usage.profile')}</span>
                    </div>
                    <span className="font-medium text-[10px]">{authStatus.name}</span>
                  </div>
                  {/* Profile ID with icon */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Fingerprint className="h-3 w-3" />
                      <span className="text-[10px]">{t('common:usage.id')}</span>
                    </div>
                    {authStatus.id && (
                      <span className="text-xs text-muted-foreground">{truncateId(authStatus.id)}</span>
                    )}
                  </div>
                  {/* API Endpoint with better styling */}
                  {authStatus.baseUrl && (
                    <div className="pt-1">
                      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground mb-1">
                        <ExternalLink className="h-3 w-3" />
                        <span>{t('common:usage.apiEndpoint')}</span>
                      </div>
                      <div className="text-[10px] font-mono bg-muted px-2 py-1.5 rounded break-all border">
                        {authStatus.baseUrl}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                // Affichage spécial pour Copilot avec informations GitHub CLI réelles
                selectedProvider === 'copilot' ? (
                  <div className="pt-2 border-t space-y-2">
                    <div className="text-[10px] text-muted-foreground">
                      {t('common:usage.copilotAuthNote', { provider: 'GitHub Copilot' }) || 'GitHub Copilot utilise l\'authentification GitHub CLI (gh auth login)'}
                    </div>
                    
                    {/* GitHub CLI Status */}
                    {isLoadingGithubStatus ? (
                      <div className="text-[10px] text-muted-foreground italic">
                        Vérification du statut GitHub...
                      </div>
                    ) : githubStatus ? (
                      githubStatus.available ? (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5 text-muted-foreground">
                              <Shield className="h-3 w-3" />
                              <span className="text-[10px]">Statut GitHub</span>
                            </div>
                            <span className={`text-[10px] font-medium ${githubStatus.isAuth ? 'text-green-500' : 'text-red-500'}`}>
                              {githubStatus.isAuth ? 'Connecté' : 'Non connecté'}
                            </span>
                          </div>
                          {githubStatus.username && (
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-1.5 text-muted-foreground">
                                <Key className="h-3 w-3" />
                                <span className="text-[10px]">Compte actif</span>
                              </div>
                              <span className="text-[10px] font-medium text-blue-500">
                                @{githubStatus.username}
                              </span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-[10px] text-red-500">
                          GitHub CLI non disponible. Installez GitHub CLI et exécutez <code className="bg-muted px-1 rounded">gh auth login</code>
                        </div>
                      )
                    ) : (
                      <div className="text-[10px] text-muted-foreground italic">
                        Impossible de vérifier le statut GitHub CLI
                      </div>
                    )}
                    
                    {/* Note sur l'absence de données d'utilisation */}
                    <div className="pt-1 border-t">
                      <div className="text-[10px] text-muted-foreground italic">
                        {t('common:usage.dataUnavailable')}
                      </div>
                      <div className="text-[10px] text-muted-foreground italic">
                        {t('common:usage.dataUnavailableDescription')}
                      </div>
                      <div className="text-[10px] text-muted-foreground mt-1">
                        Consultez le <a href="https://github.com/settings/copilot" target="_blank" rel="noopener noreferrer" className="text-blue-500 underline">dashboard GitHub Copilot</a> pour suivre votre utilisation
                      </div>
                    </div>
                  </div>
                ) : (
                  // Affichage du fallback si aucune donnée d'usage n'est disponible pour le provider sélectionné
                  !usage && selectedProvider ? (
                    <div className="pt-2 border-t text-[10px] text-muted-foreground">
                      {t('common:usage.noProfileForProvider', { provider: selectedProvider })}
                    </div>
                  ) : (
                    <div className="pt-2 border-t text-[10px] text-muted-foreground">
                      {t('common:usage.noProfileForProvider', { provider: badgeLabel }) || `Aucun profil configuré pour le provider ${badgeLabel}`}
                    </div>
                  )
                )
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* 5 Hour Usage Badge (shown when session usage >= 90%) */}
      {usage && !isLoadingUsage && usage.sessionPercent >= 90 && (
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-red-500/10 text-red-500 border-red-500/20 text-xs font-semibold">
                {Math.round(usage.sessionPercent)}%
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs max-w-xs">
              <div className="space-y-1">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground font-medium">{localizeUsageWindowLabel(usage?.usageWindows?.sessionWindowLabel, t)}</span>
                  <span className="font-semibold text-red-500">{Math.round(usage.sessionPercent)}%</span>
                </div>
                {sessionResetTime && (
                  <>
                    <div className="h-px bg-border" />
                    <div className="text-[10px] text-muted-foreground">
                      {sessionResetTime}
                    </div>
                  </>
                )}
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}