/**
 * Usage Indicator - Real-time Claude usage display in the header
 *
 * Displays current session/weekly usage as a badge with color-coded status.
 * - Hover to show breakdown popup (auto-closes on mouse leave)
 * - Click to pin popup open (stays until clicking outside)
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Activity, AlertCircle, ChevronRight, Clock, TrendingUp } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from './ui/popover';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import { useTranslation } from 'react-i18next';
import { formatTimeRemaining, localizeUsageWindowLabel, hasHardcodedText } from '@shared/utils/format-time';
import type { UsageSnapshot, ProfileUsageSummary, ClaudeUsageData } from '@shared/types';
import { useProviderContext } from './ProviderContext';
import { PROVIDER_MODELS_MAP } from '@shared/constants/models';
import {AppSection} from "@/components/settings/AppSettings";

// Import extracted components and utilities
import { OpenAIUsageContent } from './usage/OpenAIUsageContent';
import { CopilotUsageContent } from './usage/CopilotUsageContent';
import { ReauthContent } from './usage/ReauthContent';
import { DefaultUsageContent } from './usage/DefaultUsageContent';
import { ProfileRenderer } from './usage/ProfileRenderer';
import { getColorClass, getBadgeColorClasses } from '../utils/usageColors';
import { THRESHOLD_WARNING, THRESHOLD_ELEVATED } from './usage/usageConstants';
import { formatUsageValue } from '@shared/utils/format-usage';

// All provider keys from the canonical map (including both 'anthropic' and 'claude' aliases)
const KNOWN_PROVIDERS = new Set(
  Object.keys(PROVIDER_MODELS_MAP)
);

export function UsageIndicator() {
  const { t, i18n } = useTranslation(['common']);
  const [usage, setUsage] = useState<UsageSnapshot | null>(null);
  const [otherProfiles, setOtherProfiles] = useState<ProfileUsageSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAvailable, setIsAvailable] = useState(false);
  const [activeProfileNeedsReauth, setActiveProfileNeedsReauth] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isPinned, setIsPinned] = useState(false);
  const [providerProfile, setProviderProfile] = useState<any>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  // Deduplication: track in-flight fetch to prevent concurrent API calls (429 rate limits)
  const pendingFetchRef = useRef<Promise<void> | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { selectedProvider } = useProviderContext();

  /**
   * Helper function to get initials from a profile name
   */
  const getInitials = (name: string): string => {
    if (!name || name.trim().length === 0) {
      return 'UN'; // Unknown
    }
    const words = name.trim().split(/\s+/);
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  /**
   * Navigate to settings accounts tab
   */
  const handleOpenAccounts = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Close the popover first
    setIsOpen(false);
    setIsPinned(false);
    // Dispatch custom event to open settings with accounts section
    // Small delay to allow popover to close first
    setTimeout(() => {
      const event = new CustomEvent<AppSection>('open-app-settings', {
        detail: 'accounts'
      });
      globalThis.dispatchEvent(event);
    }, 100);
  }, []);

  /**
   * Centralized, deduplicated usage fetch with retry.
   * Prevents multiple concurrent API calls that trigger 429 rate limits.
   * If the fetch returns null, retries once after a short delay.
   */
  const fetchUsageDeduplicated = useCallback(async (provider: string, retryCount = 0): Promise<void> => {
    // If a fetch is already in-flight, piggyback on it instead of firing a new one
    if (pendingFetchRef.current) {
      console.log('[UsageIndicator] fetchUsageDeduplicated: piggyback on in-flight fetch for', provider);
      return pendingFetchRef.current;
    }

    const doFetch = async () => {
      console.log('[UsageIndicator] fetchUsageDeduplicated: starting IPC call for', provider, 'retry', retryCount);
      try {
        // Race the IPC call against a 20-second timeout so we never hang indefinitely.
        const ipcPromise = globalThis.electronAPI.requestUsageUpdate(provider);
        const timeoutPromise = new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('[UsageIndicator] requestUsageUpdate timed out after 20s')), 20000)
        );
        const result = await Promise.race([ipcPromise, timeoutPromise]);
        console.log('[UsageIndicator] fetchUsageDeduplicated: IPC result', {
          success: result?.success,
          hasData: !!result?.data,
          providerName: result?.data?.providerName,
          sessionPercent: result?.data?.sessionPercent,
        });
        if (result.success && result.data) {
          if (provider && result.data.providerName && result.data.providerName !== provider) {
            console.log('[UsageIndicator] fetchUsageDeduplicated: FILTERED OUT — providerName mismatch', result.data.providerName, '!==', provider);
            return;
          }
          setUsage(result.data);
          setIsAvailable(true);
          setIsLoading(false);
          console.log('[UsageIndicator] fetchUsageDeduplicated: setIsLoading(false) called');
        } else if (retryCount < 2) {
          // API returned null (429 rate limit, token refresh failure, etc.)
          // Retry after a short backoff instead of immediately showing "N/D"
          await new Promise<void>((resolve) => {
            retryTimeoutRef.current = setTimeout(resolve, 3000 * (retryCount + 1));
          });
          pendingFetchRef.current = null; // Allow the retry to create a new fetch
          return fetchUsageDeduplicated(provider, retryCount + 1);
        } else {
          // All retries exhausted — only set unavailable if we never had data
          setIsLoading(false);
          // Keep existing data if we have it (stale-while-revalidate)
          setIsAvailable((prev) => prev); // No-op: don't clear if we had data before
        }
      } catch (error) {
        console.warn('[UsageIndicator] Failed to fetch usage data:', error);
        setIsLoading(false);
      } finally {
        pendingFetchRef.current = null;
      }
    };

    pendingFetchRef.current = doFetch();
    return pendingFetchRef.current;
  }, []);

  /**
   * Handle swapping to a different profile
   * Uses optimistic UI update for immediate feedback, then fetches fresh data
   */
  const handleSwapProfile = useCallback(async (e: React.MouseEvent, profileId: string) => {
    e.preventDefault();
    e.stopPropagation();

    // Capture previous state for revert (before any changes)
    const previousUsage = usage;
    const previousOtherProfiles = otherProfiles;

    // Find the profile we're swapping to
    const targetProfile = otherProfiles.find(p => p.profileId === profileId);
    if (!targetProfile) {
      console.error('[UsageIndicator] Target profile not found:', profileId);
      return;
    }

    // Optimistic update: immediately swap profiles in the UI
    // 1. Convert a current active profile to a ProfileUsageSummary for the "other" list
    const currentActiveAsSummary: ProfileUsageSummary = {
      profileId: usage?.profileId || '',
      profileName: usage?.profileName || '',
      profileEmail: usage?.profileEmail,
      sessionPercent: usage?.sessionPercent || 0,
      weeklyPercent: usage?.weeklyPercent || 0,
      sessionResetTimestamp: usage?.sessionResetTimestamp,
      weeklyResetTimestamp: usage?.weeklyResetTimestamp,
      isAuthenticated: true,
      isRateLimited: false,
      availabilityScore: 100 - Math.max(usage?.sessionPercent || 0, usage?.weeklyPercent || 0),
      isActive: false, // It's no longer active
      needsReauthentication: usage?.needsReauthentication,
    };

    // 2. Convert target profile to a UsageSnapshot for the active display
    const newActiveUsage: UsageSnapshot = {
      profileId: targetProfile.profileId,
      profileName: targetProfile.profileName,
      profileEmail: targetProfile.profileEmail,
      sessionPercent: targetProfile.sessionPercent,
      weeklyPercent: targetProfile.weeklyPercent,
      sessionResetTimestamp: targetProfile.sessionResetTimestamp,
      weeklyResetTimestamp: targetProfile.weeklyResetTimestamp,
      fetchedAt: new Date(),
      needsReauthentication: targetProfile.needsReauthentication,
    };

    // 3. Update the other profiles list: remove target, add current active
    const newOtherProfiles = otherProfiles
        .filter(p => p.profileId !== profileId)
        .concat(usage ? [currentActiveAsSummary] : [])
        .sort((a, b) => b.availabilityScore - a.availabilityScore);

    // Apply optimistic update immediately
    setUsage(newActiveUsage);
    setOtherProfiles(newOtherProfiles);

    try {
      // Actually switch the profile on the backend
      const result = await globalThis.electronAPI.setActiveClaudeProfile(profileId);
      if (result.success) {
        // Fetch fresh data in the background (will update via event listeners)
        await globalThis.electronAPI.requestUsageUpdate();
        globalThis.electronAPI.requestAllProfilesUsage?.();

        // If the profile needs re-authentication, open Settings > Accounts
        // so the user can complete the re-auth flow
        if (targetProfile.needsReauthentication) {
          // Close the popover first
          setIsOpen(false);
          setIsPinned(false);
          // Open settings with accounts section after a short delay
          setTimeout(() => {
            const event = new CustomEvent<AppSection>('open-app-settings', {
              detail: 'accounts'
            });
            globalThis.dispatchEvent(event);
          }, 100);
        }
      } else {
        // Revert to captured previous state
        console.error('[UsageIndicator] Failed to swap profile, reverting');
        if (previousUsage) setUsage(previousUsage);
        setOtherProfiles(previousOtherProfiles);
      }
    } catch (error) {
      console.error('[UsageIndicator] Failed to swap profile:', error);
      // Revert to captured previous state
      if (previousUsage) setUsage(previousUsage);
      setOtherProfiles(previousOtherProfiles);
    }
  }, [usage, otherProfiles]);

  /**
   * Handle mouse enter - show popup after short delay (unless pinned)
   */
  const handleMouseEnter = useCallback(() => {
    if (isPinned) return;
    // Clear any pending close timeout
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    // Open after short delay for smoother UX
    hoverTimeoutRef.current = setTimeout(() => {
      setIsOpen(true);
    }, 150);
  }, [isPinned]);

  /**
   * Handle mouse leave - close popup after delay (unless pinned)
   */
  const handleMouseLeave = useCallback(() => {
    if (isPinned) return;
    // Clear any pending open timeout
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    // Close after delay to allow moving to popup content
    hoverTimeoutRef.current = setTimeout(() => {
      setIsOpen(false);
    }, 300);
  }, [isPinned]);

  /**
   * Handle click on trigger - toggle pinned state
   */
  const handleTriggerClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    if (isPinned) {
      // Clicking when pinned unpins and closes
      setIsPinned(false);
      setIsOpen(false);
    } else {
      // Clicking when not pinned pins it open
      setIsPinned(true);
      setIsOpen(true);
    }
  }, [isPinned]);

  /**
   * Handle popover open change (e.g., clicking outside)
   */
  const handleOpenChange = useCallback((open: boolean) => {
    if (!open) {
      // Closing from outside click
      setIsOpen(false);
      setIsPinned(false);
    }
  }, []);

  // Effect to check OAuth status for the selected provider
  useEffect(() => {
    if (selectedProvider === 'anthropic') {
      const checkOAuthStatus = async () => {
        try {
          const profilesResult = await globalThis.electronAPI.invoke('claude:profilesGet');
          
          if (profilesResult.success && profilesResult.data?.profiles) {
            const oauthProfile = profilesResult.data.profiles.find((profile: any) => 
              profile.isAuthenticated === true
            );
            
            if (oauthProfile) {
              setProviderProfile(oauthProfile);
              fetchUsageDeduplicated(selectedProvider);
            } else {
              setProviderProfile(null);
            }
          }
        } catch (error) {
          console.warn('[UsageIndicator] Failed to check provider profiles:', error);
          setProviderProfile(null);
        }
      };
      
      checkOAuthStatus();
    } else {
      // For non-Anthropic providers, clear the OAuth profile
      // Usage data comes from the standard usage polling mechanism
      setProviderProfile(null);
    }
  }, [selectedProvider, fetchUsageDeduplicated]);


  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  // Real-time polling effect - refresh usage data every 30 seconds
  useEffect(() => {
    // Clear any existing interval
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    // Helper to fetch and apply fresh usage data (uses deduplicated fetch)
    const fetchAndApplyUsage = async () => {
      await fetchUsageDeduplicated(selectedProvider);

      try {
        const allResult = await globalThis.electronAPI.requestAllProfilesUsage?.();
        if (allResult?.success && allResult?.data) {
          const nonActiveProfiles = allResult.data.allProfiles.filter(p => !p.isActive);
          setOtherProfiles(nonActiveProfiles);
          const activeProfile = allResult.data.allProfiles.find(p => p.isActive);
          if (activeProfile?.needsReauthentication) {
            setActiveProfileNeedsReauth(true);
          }
        }
      } catch (error) {
        console.warn('[UsageIndicator] Failed to refresh all profiles usage:', error);
      }
    };

    // Only set up polling for providers that support usage tracking
    if (selectedProvider && KNOWN_PROVIDERS.has(selectedProvider.toLowerCase())) {

      // Set up polling interval (30 seconds)
      pollingIntervalRef.current = setInterval(async () => {
        setIsRefreshing(true);

        try {
          await fetchAndApplyUsage();
          setLastRefreshTime(new Date());
        } finally {
          // Brief visual feedback of refresh
          setTimeout(() => setIsRefreshing(false), 1000);
        }
      }, 30000); // 30 seconds

      // Also refresh immediately when provider changes
      fetchAndApplyUsage();
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [selectedProvider, fetchUsageDeduplicated]);

  // Helper function to get reset time with fallback logic
  const getResetTime = (timestamp: string | undefined, fallbackTime: string | undefined) => {
    if (timestamp) {
      const formattedTime = formatTimeRemaining(timestamp, t);
      return formattedTime ?? (hasHardcodedText(fallbackTime) ? undefined : fallbackTime);
    }
    return hasHardcodedText(fallbackTime) ? undefined : fallbackTime;
  };

  // Get formatted reset times (calculated dynamically from timestamps)
  const sessionResetTime = getResetTime(usage?.sessionResetTimestamp, usage?.sessionResetTime);
  const weeklyResetTime = getResetTime(usage?.weeklyResetTimestamp, usage?.weeklyResetTime);

  useEffect(() => {
    // When selectedProvider changes, clear stale data from previous provider
    // to prevent showing wrong provider's account/usage info
    console.log('[UsageIndicator] Effect @411 running, selectedProvider =', JSON.stringify(selectedProvider));
    setUsage(null);
    setOtherProfiles([]);
    setIsAvailable(false);
    setIsLoading(true);
    setActiveProfileNeedsReauth(false);

    // Listen for usage updates from main process
    const unsubscribe = globalThis.electronAPI.onUsageUpdated((snapshot: UsageSnapshot) => {
      console.log('[UsageIndicator] onUsageUpdated received:', {
        providerName: snapshot?.providerName,
        sessionPercent: snapshot?.sessionPercent,
        selectedProvider,
      });
      // Only accept snapshots that match the selected provider.
      // When selectedProvider is empty (still loading), reject all snapshots to avoid
      // accepting a wrong-provider snapshot that would linger after the real provider loads.
      if (!selectedProvider) {
        console.log('[UsageIndicator] onUsageUpdated: REJECTED — selectedProvider is empty');
        return;
      }
      // Only reject if the snapshot explicitly declares a *different* provider.
      // Snapshots from the CLI path have no providerName — accept them for any provider.
      if (snapshot.providerName && snapshot.providerName !== selectedProvider) {
        console.log('[UsageIndicator] onUsageUpdated: REJECTED — providerName mismatch', snapshot.providerName, '!==', selectedProvider);
        return;
      }
      console.log('[UsageIndicator] onUsageUpdated: ACCEPTED — calling setIsLoading(false)');
      setUsage(snapshot);
      setIsAvailable(true);
      setIsLoading(false);
    });

    // Listen for provider changes to update UI immediately
    const handleProviderChange = (event: CustomEvent) => {
      const { provider } = event.detail;
      if (provider !== selectedProvider) return;

      // Clear stale data from previous provider and show loading
      setUsage(null);
      setOtherProfiles([]);
      setIsAvailable(false);
      setIsLoading(true);
      setActiveProfileNeedsReauth(false);

      // Fetch fresh data using deduplicated fetch (with retry on failure)
      fetchUsageDeduplicated(provider);
    };

    globalThis.addEventListener('providerChanged', handleProviderChange as EventListener);

    // Listen for all profiles usage updates (for multi-profile display)
    const unsubscribeAllProfiles = globalThis.electronAPI.onAllProfilesUsageUpdated?.((allProfilesUsage) => {
      // Filter out the active profile - we only want to show "other" profiles
      const nonActiveProfiles = allProfilesUsage.allProfiles.filter(p => !p.isActive);
      setOtherProfiles(nonActiveProfiles);
      // Track if active profile needs re-auth
      const activeProfile = allProfilesUsage.allProfiles.find(p => p.isActive);
      setActiveProfileNeedsReauth(activeProfile?.needsReauthentication ?? false);
    });

    // Request initial usage on mount for the selected provider (deduplicated with retry)
    if (selectedProvider && KNOWN_PROVIDERS.has(selectedProvider.toLowerCase())) {
      console.log('[UsageIndicator] Effect @411: calling fetchUsageDeduplicated for', selectedProvider);
      fetchUsageDeduplicated(selectedProvider);
    } else if (selectedProvider) {
      // Provider is set but not a known/supported provider — stop loading
      console.log('[UsageIndicator] Effect @411: unknown provider, setIsLoading(false)');
      setIsLoading(false);
    } else {
      // selectedProvider is empty — isLoading stays true waiting for ProviderContext
      console.log('[UsageIndicator] Effect @411: selectedProvider is empty, keeping isLoading=true');
    }
    // When selectedProvider is empty (''), keep isLoading=true to avoid
    // flashing "N/D" while ProviderContext resolves the real provider

    // Request all profiles usage immediately on mount (so other accounts show right away)
    globalThis.electronAPI.requestAllProfilesUsage?.().then((result) => {
      if (result.success && result.data) {
        const nonActiveProfiles = result.data.allProfiles.filter(p => !p.isActive);
        setOtherProfiles(nonActiveProfiles);
        // Track if active profile needs re-auth (even if main usage is unavailable)
        const activeProfile = result.data.allProfiles.find(p => p.isActive);
        if (activeProfile?.needsReauthentication) {
          setActiveProfileNeedsReauth(true);
        }
      }
    });

    return () => {
      unsubscribe();
      unsubscribeAllProfiles?.();
      globalThis.removeEventListener('providerChanged', handleProviderChange as EventListener);
    };
  }, [selectedProvider, fetchUsageDeduplicated]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-muted/50 text-muted-foreground">
        <Activity className="h-3.5 w-3.5 motion-safe:animate-pulse" />
        <span className="text-xs font-semibold">{t('common:usage.loading')}</span>
      </div>
    );
  }
  // Show unavailable state - with better messaging based on cause
  if (!isAvailable || !usage) {
    const needsReauth = activeProfileNeedsReauth;
    
    // Debug: Log current provider and known providers
    
    // Debug OpenAI
    if (selectedProvider?.toLowerCase() === 'openai') {
      let debugProfiles = [];
      if (typeof globalThis !== 'undefined' && (globalThis as any).debugProfiles) {
        debugProfiles = (globalThis as any).debugProfiles;
      }
      const openaiError = typeof globalThis === 'undefined' ? undefined : (globalThis as any).lastOpenAIUsageError;
      return (
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-muted/50 text-muted-foreground"
                aria-label={t('common:usage.dataUnavailable')}
              >
                <Activity className="h-3.5 w-3.5" />
                <span className="text-xs font-semibold">{t('common:usage.dataUnavailable')}</span>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs w-80">
              <div className="space-y-1">
                <p className="font-medium">{t('common:usage.dataUnavailable')}</p>
                <p className="text-muted-foreground text-[10px]">
                  <span>
                    {t('common:usage.openaiHelp.text')}{' '}
                    <a
                      href="https://platform.openai.com/usage"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-bold"
                    >
                      {t('common:usage.openaiHelp.link')}
                    </a>
                  </span>
                </p>
                {openaiError && (
                  <div className="mt-2 p-1 bg-red-50 border border-red-200 rounded text-[10px] text-red-700">
                    <b>{t('common:usage.openaiError')}</b> {openaiError}
                  </div>
                )}
                <div className="mt-2 p-1 bg-muted/30 rounded text-[10px]">
                  <b>{t('common:usage.debugProfiles')}</b>
                  <ul>
                    {debugProfiles.length > 0 ? debugProfiles.map((p: any) => (
                      <li key={`${p.name}-${p.baseUrl}`}>{p.name} | {p.baseUrl} | provider: {p.detectedProvider}</li>
                    )) : <li>{t('common:usage.noProfileDetected')}</li>}
                  </ul>
                  <div>{t('common:usage.selectedProvider', { provider: selectedProvider })}</div>
                </div>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    // Provider non reconnu (absent de PROVIDER_MODELS_MAP)
    if (selectedProvider && !KNOWN_PROVIDERS.has(selectedProvider.toLowerCase())) {
      return (
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-muted/50 text-muted-foreground"
                aria-label={t('common:usage.dataUnavailable')}
              >
                <Activity className="h-3.5 w-3.5" />
                <span className="text-xs font-semibold">{t('common:usage.notAvailable')}</span>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs w-64">
              <div className="space-y-1">
                <p className="font-medium">{t('common:usage.dataUnavailable')}</p>
                <p className="text-muted-foreground text-[10px]">
                  {t('common:usage.providerNotSupported')}
                </p>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }
    // Re-authentification nécessaire
    if (needsReauth) {
      return <ReauthContent onOpenAccounts={handleOpenAccounts} />;
    }
    // Fallback générique pour les providers qui fonctionnent mais n'ont pas de données
    return (
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-muted/50 text-muted-foreground">
              <Activity className="h-3.5 w-3.5" />
              <span className="text-xs font-semibold">{t('common:usage.notAvailable')}</span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-xs w-64">
            <div className="space-y-1">
              <p className="font-medium">{t('common:usage.dataUnavailable')}</p>
              <p className="text-muted-foreground text-[10px]">
                {selectedProvider === 'anthropic'
                  ? t('common:usage.dataUnavailableAnthropic')
                  : t('common:usage.dataUnavailableDescription')
                }
              </p>
              {selectedProvider === 'anthropic' && (
                <a
                  href="https://claude.ai/settings"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-primary font-medium underline hover:text-primary/80 block mt-1"
                >
                  claude.ai/settings
                </a>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // Determine colors and labels based on the LIMITING factor (higher of session/weekly)
  const sessionPercent = usage.sessionPercent;
  const weeklyPercent = usage.weeklyPercent;
  const limitingPercent = Math.max(sessionPercent, weeklyPercent);

  // Badge color based on the limiting (higher) percentage
  // Override to red/destructive when re-auth is needed
  const badgeColorClasses = usage.needsReauthentication
      ? 'text-red-500 bg-red-500/10 border-red-500/20'
      : getBadgeColorClasses(limitingPercent);

  // Individual colors for session and weekly in the badge
  const sessionColorClass = getColorClass(sessionPercent);
  const weeklyColorClass = getColorClass(weeklyPercent);

  const sessionLabel = localizeUsageWindowLabel(
      usage?.usageWindows?.sessionWindowLabel,
      t,
      'common:usage.sessionDefault'
  );
  const weeklyLabel = localizeUsageWindowLabel(
      usage?.usageWindows?.weeklyWindowLabel,
      t,
      'common:usage.weeklyDefault'
  );

  
  const maxUsage = Math.max(usage.sessionPercent, usage.weeklyPercent);

  // Provider detection
  const isOpenAI = usage.providerName === 'openai';
  const isCopilot = usage.providerName === 'copilot';

  const hasErrorCondition = 
    usage.needsReauthentication ||
    (isCopilot && (usage as any).error && (usage as any).error !== 'NONE') ||
    maxUsage >= THRESHOLD_WARNING;

  let Icon;
  if (hasErrorCondition) {
    Icon = AlertCircle;
  } else if (maxUsage >= THRESHOLD_ELEVATED) {
    Icon = TrendingUp;
  } else {
    Icon = Activity;
  }

  // Define renderUsageContent function after all variables are calculated
  const renderUsageContent = () => {
    if (usage.needsReauthentication) {
      return <ReauthContent onOpenAccounts={handleOpenAccounts} />;
    }
    
    if (isOpenAI) {
      return <OpenAIUsageContent usage={usage} />;
    }
    
    if (isCopilot && selectedProvider === 'copilot') {
      return <CopilotUsageContent usage={usage} />;
    }
    
    return <DefaultUsageContent usage={usage} sessionResetTime={sessionResetTime} weeklyResetTime={weeklyResetTime} sessionLabel={sessionLabel} weeklyLabel={weeklyLabel} />;
  };

  const renderRealTimeIndicator = () => {
    if (isRefreshing) {
      return (
        <>
          <Activity className="h-2.5 w-2.5 motion-safe:animate-spin" />
          <span>{t('common:usage.updating')}</span>
        </>
      );
    }

    if (lastRefreshTime) {
      const minutesSinceUpdate = Math.floor((Date.now() - lastRefreshTime.getTime()) / 60000);
      return (
        <>
          <Clock className="h-2.5 w-2.5" />
          <span>{t('common:usage.lastUpdate', { minutes: minutesSinceUpdate })}</span>
        </>
      );
    }

    return <span>{t('common:usage.realTime')}</span>;
  };

  const renderUsageIndicatorContent = () => {
    if (usage.needsReauthentication) {
      return (
        <span className="text-xs font-semibold text-red-500" title="Needs re-authentication">!</span>
      );
    }

    if (isOpenAI) {
      return (
        <div className="flex items-center gap-0.5 text-xs font-semibold font-mono">
          <span className="text-green-500" title="OpenAI Cost">${formatUsageValue(usage.weeklyUsageValue, i18n.language)}</span>
        </div>
      );
    }

    if (isCopilot) {
      return (
        <div className="flex items-center gap-0.5 text-xs font-semibold font-mono">
          <span className="text-blue-500" title="Copilot Cost">{formatUsageValue(usage.copilotUsageDetails?.totalTokens, i18n.language)}T</span>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-0.5 text-xs font-semibold font-mono">
        <span className={sessionColorClass} title="Session usage">{Math.round(sessionPercent)}</span>
        <span className="text-muted-foreground/50">│</span>
        <span className={weeklyColorClass} title="Weekly usage">{Math.round(weeklyPercent)}</span>
      </div>
    );
  };

  return (
      <Popover open={isOpen} onOpenChange={handleOpenChange}>
        <PopoverTrigger asChild>
          <button
              className={`flex items-center gap-1 px-2 py-1.5 rounded-md border transition-all hover:opacity-80 ${badgeColorClasses}`}
              aria-label={t('common:usage.usageStatusAriaLabel')}
              onMouseEnter={handleMouseEnter}
              onMouseLeave={handleMouseLeave}
              onClick={handleTriggerClick}
          >
            <Icon className={`h-3.5 w-3.5 shrink-0 ${isRefreshing ? 'motion-safe:animate-spin' : ''}`} />
            {renderUsageIndicatorContent()}
          </button>
        </PopoverTrigger>
        <PopoverContent
            side="bottom"
            align="end"
            className="text-xs w-72 p-0"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
          <div className="p-3 space-y-3">
            {/* Header with overall status */}
            <div className="flex items-center justify-between pb-2 border-b">
              <div className="flex items-center gap-1.5">
                <Icon className="h-3.5 w-3.5" />
                <span className="font-semibold text-xs">{t('common:usage.usageBreakdown')}</span>
              </div>
              {/* Real-time indicator */}
              <div className="flex items-center gap-1 text-[9px] text-muted-foreground">
                {renderRealTimeIndicator()}
              </div>
            </div>

            {/* Re-auth required prompt - shown when active profile needs re-authentication */}
            {renderUsageContent()}

            {/* Active account footer - clickable to go to settings */}
            <button
                type="button"
                onClick={handleOpenAccounts}
                className={`w-full pt-3 border-t flex items-center gap-2.5 hover:bg-muted/50 -mx-3 px-3 ${otherProfiles.length === 0 ? '-mb-3 pb-3 rounded-b-md' : 'pb-2'} transition-colors cursor-pointer group`}
            >
              {/* Initials Avatar with warning indicator for re-auth needed */}
              <div className="relative">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    usage.needsReauthentication ? 'bg-red-500/10' : 'bg-primary/10'
                }`}>
                <span className={`text-xs font-semibold ${
                    usage.needsReauthentication ? 'text-red-500' : 'text-primary'
                }`}>
                  {getInitials(providerProfile ? providerProfile.name : usage.profileName)}
                </span>
                </div>
                {/* Status dot for re-auth needed */}
                {usage.needsReauthentication && (
                    <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-background" />
                )}
              </div>

              {/* Account Info */}
              <div className="flex-1 min-w-0 text-left">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground font-medium">
                    {t('common:usage.activeAccount')}
                  </span>
                  {usage.needsReauthentication && (
                    <span className="text-[9px] px-1.5 py-0.5 bg-red-500/10 text-destructive rounded font-semibold">
                      {t('common:usage.needsReauth')}
                    </span>
                  )}
                </div>
                <div className={`font-medium text-xs truncate ${
                  usage.needsReauthentication ? 'text-destructive' : 'text-primary'
                }`}>
                  {providerProfile ? providerProfile.email || providerProfile.name : (usage.profileEmail || usage.profileName)}
                </div>
              </div>

              {/* Chevron */}
              <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
            </button>

            {/* Other profiles section - sorted by availability */}
            {otherProfiles.length > 0 && (
                <div className="pt-2 -mx-3 px-3 -mb-3 pb-3 space-y-1">
                  <div className="text-[10px] text-muted-foreground font-medium mb-1.5">
                    {t('common:usage.otherAccounts')}
                  </div>
                  {otherProfiles.map((profile) => {
                    // Convert ProfileUsageSummary to ClaudeUsageData
                    const usageData: ClaudeUsageData = {
                      sessionUsagePercent: profile.sessionPercent,
                      sessionResetTime: profile.sessionResetTimestamp || '',
                      weeklyUsagePercent: profile.weeklyPercent,
                      weeklyResetTime: profile.weeklyResetTimestamp || '',
                      lastUpdated: new Date()
                    };
                    
                    return (
                      <ProfileRenderer
                        key={profile.profileId}
                        account={{
                          id: profile.profileId,
                          name: profile.profileName,
                          email: profile.profileEmail,
                          oauthToken: '',
                          configDir: '',
                          isDefault: false,
                          description: '',
                          createdAt: new Date(),
                          lastUsedAt: new Date(),
                          usage: usageData,
                          rateLimitEvents: []
                        }}
                        isActive={false}
                        onClick={(e) => handleSwapProfile(e, profile.profileId)}
                      />
                    );
                  })}
                </div>
            )}
          </div>
        </PopoverContent>
      </Popover>
  );
}
