/**
 * Usage Indicator Dumb Component - Pure UI display
 *
 * Ce composant est "dumb" - il affiche seulement les données qu'il reçoit
 * Toute la logique métier est gérée par le backend via CredentialService
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Activity, TrendingUp, AlertCircle, LogIn } from 'lucide-react';
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
import { formatTimeRemaining, } from '@shared/utils/format-time';
import { credentialService, type UsageData, type CredentialConfig } from '@shared/services/credentialService';
import { useProviderContext } from './ProviderContext';
import {AppSection} from "@/components/settings/AppSettings";

// Seuils pour le codage couleur
const THRESHOLD_CRITICAL = 95;
const THRESHOLD_WARNING = 91;
const THRESHOLD_ELEVATED = 71;

/**
 * Obtenir la classe de couleur basée sur le pourcentage d'usage
 */
const getColorClass = (percent: number): string => {
  if (percent >= THRESHOLD_CRITICAL) return 'text-red-500';
  if (percent >= THRESHOLD_WARNING) return 'text-orange-500';
  if (percent >= THRESHOLD_ELEVATED) return 'text-yellow-500';
  return 'text-green-500';
};

/**
 * Obtenir les classes de couleur pour les badges
 */
const getBadgeColorClasses = (percent: number): string => {
  if (percent >= THRESHOLD_CRITICAL) return 'text-red-500 bg-red-500/10 border-red-500/20';
  if (percent >= THRESHOLD_WARNING) return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
  if (percent >= THRESHOLD_ELEVATED) return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
  return 'text-green-500 bg-green-500/10 border-green-500/20';
};

/**
 * Obtenir les initiales à partir d'un nom
 */
const getInitials = (name: string): string => {
  if (!name || name.trim().length === 0) {
    return 'UN';
  }
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
};

/**
 * Formater les grandes valeurs avec notation compacte
 */
const _formatUsageValue = (value?: number | null): string | undefined => {
  if (value == null) return undefined;

  if (typeof Intl !== 'undefined' && Intl.NumberFormat) {
    try {
      return new Intl.NumberFormat('fr-FR', {
        notation: 'compact',
        compactDisplay: 'short',
        maximumFractionDigits: 2
      }).format(value);
    } catch {
      // Intl peut échouer dans certains environnements
    }
  }
  return value.toString();
};

interface UsageIndicatorDumbProps {
  // Props optionnelles pour override si besoin
  selectedProvider?: string;
}

export function UsageIndicatorDumb({ selectedProvider: propSelectedProvider }: UsageIndicatorDumbProps = {}) {
  const { t, i18n } = useTranslation(['common']);
  const { selectedProvider: contextProvider } = useProviderContext();
  const selectedProvider = propSelectedProvider || contextProvider;

  // États locaux - seulement pour l'UI
  const [usageData, setUsageData] = useState<UsageData | null>(null);
  const [credential, setCredential] = useState<CredentialConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAvailable, setIsAvailable] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isPinned, setIsPinned] = useState(false);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Naviguer vers les paramètres des comptes
   */
  const handleOpenAccounts = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsOpen(false);
    setIsPinned(false);
    setTimeout(() => {
      const event = new CustomEvent<AppSection>('open-app-settings', {
        detail: 'accounts'
      });
      window.dispatchEvent(event);
    }, 100);
  }, []);

  /**
   * Gérer le changement de provider
   */
  const _handleProviderSwitch = useCallback(async (e: React.MouseEvent, provider: string, type: 'oauth' | 'api_key', profileId?: string) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      await credentialService.setActiveProvider(provider, type, profileId);
    } catch (error) {
      console.error('[UsageIndicatorDumb] Failed to switch provider:', error);
    }
  }, []);

  /**
   * Gérer le survol de la souris
   */
  const handleMouseEnter = useCallback(() => {
    if (isPinned) return;
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    hoverTimeoutRef.current = setTimeout(() => {
      setIsOpen(true);
    }, 150);
  }, [isPinned]);

  /**
   * Gérer la sortie de souris
   */
  const handleMouseLeave = useCallback(() => {
    if (isPinned) return;
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    hoverTimeoutRef.current = setTimeout(() => {
      setIsOpen(false);
    }, 300);
  }, [isPinned]);

  /**
   * Gérer le clic sur le trigger
   */
  const handleTriggerClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    if (isPinned) {
      setIsPinned(false);
      setIsOpen(false);
    } else {
      setIsPinned(true);
      setIsOpen(true);
    }
  }, [isPinned]);

  /**
   * Gérer le changement d'état du popover
   */
  const handleOpenChange = useCallback((open: boolean) => {
    if (!open) {
      setIsOpen(false);
      setIsPinned(false);
    }
  }, []);

  // Effet pour charger les données initiales et s'abonner aux événements
  useEffect(() => {
    const loadData = async () => {
      try {
        // Charger le credential actif
        const activeCredential = await credentialService.getActiveCredential();
        setCredential(activeCredential);

        // Charger les données d'usage pour le provider sélectionné
        if (selectedProvider) {
          const data = await credentialService.getUsageData(selectedProvider);
          setUsageData(data);
          setIsAvailable(!!data);
        }
        
        setIsLoading(false);
      } catch (error) {
        console.error('[UsageIndicatorDumb] Failed to load initial data:', error);
        setIsLoading(false);
        setIsAvailable(false);
      }
    };

    loadData();

    // S'abonner aux événements du CredentialService
    const handleCredentialUpdated = (newCredential: CredentialConfig | null) => {
      setCredential(newCredential);
    };

    const handleUsageChanged = (data: UsageData) => {
      if (data.provider === selectedProvider) {
        setUsageData(data);
        setIsAvailable(true);
        setIsLoading(false);
      }
    };

    const handleProviderSwitched = (data: { provider: string; type: 'oauth' | 'api_key' }) => {
      // Recharger les données d'usage quand le provider change
      if (data.provider === selectedProvider) {
        credentialService.getUsageData(data.provider).then(setUsageData);
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
  }, [selectedProvider]);

  // Nettoyer le timeout au démontage
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

  // État de chargement
  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-muted/50 text-muted-foreground">
        <Activity className="h-3.5 w-3.5 motion-safe:animate-pulse" />
        <span className="text-xs font-semibold">{t('common:usage.loading')}</span>
      </div>
    );
  }

  // État indisponible
  if (!isAvailable || !usageData) {
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
                {t('common:usage.dataUnavailableDescription')}
              </p>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // Calculer les couleurs et labels
  const sessionPercent = usageData.usage.sessionPercent || 0;
  const weeklyPercent = usageData.usage.weeklyPercent || 0;
  const limitingPercent = Math.max(sessionPercent, weeklyPercent);

  const badgeColorClasses = usageData.usage.needsReauthentication
    ? 'text-red-500 bg-red-500/10 border-red-500/20'
    : getBadgeColorClasses(limitingPercent);

  const sessionColorClass = getColorClass(sessionPercent);
  const weeklyColorClass = getColorClass(weeklyPercent);

  const sessionResetTime = usageData.usage.sessionResetTimestamp
    ? formatTimeRemaining(usageData.usage.sessionResetTimestamp.toString(), t)
    : undefined;

  const weeklyResetTime = usageData.usage.weeklyResetTimestamp
    ? formatTimeRemaining(usageData.usage.weeklyResetTimestamp.toString(), t)
    : undefined;

  const maxUsage = Math.max(sessionPercent, weeklyPercent);
  const Icon = usageData.usage.needsReauthentication
    ? AlertCircle
    : maxUsage >= THRESHOLD_WARNING
      ? AlertCircle
      : maxUsage >= THRESHOLD_ELEVATED
        ? TrendingUp
        : Activity;

  // Rendu du composant
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
          <Icon className="h-3.5 w-3.5 shrink-0" />
          {usageData.usage.needsReauthentication ? (
            <span className="text-xs font-semibold text-red-500" title={t('common:usage.needsReauth')}>
              !
            </span>
          ) : (
            <div className="flex items-center gap-0.5 text-xs font-semibold font-mono">
              <span className={sessionColorClass} title={t('common:usage.sessionShort')}>
                {Math.round(sessionPercent)}
              </span>
              <span className="text-muted-foreground/50">│</span>
              <span className={weeklyColorClass} title={t('common:usage.weeklyShort')}>
                {Math.round(weeklyPercent)}
              </span>
            </div>
          )}
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
          {/* Header avec statut global */}
          <div className="flex items-center gap-1.5 pb-2 border-b">
            <Icon className="h-3.5 w-3.5" />
            <span className="font-semibold text-xs">{t('common:usage.usageBreakdown')}</span>
          </div>

          {/* Alerte de réauthentification */}
          {usageData.usage.needsReauthentication && (
            <div className="py-2 space-y-3">
              <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-destructive/10 border border-destructive/20">
                <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-xs font-medium text-destructive">
                    {t('common:usage.reauthRequired')}
                  </p>
                  <p className="text-[10px] text-muted-foreground leading-relaxed">
                    {t('common:usage.reauthRequiredDescription')}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleOpenAccounts}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors text-xs font-medium"
              >
                <LogIn className="h-3.5 w-3.5" />
                {t('common:usage.reauthButton')}
              </button>
            </div>
          )}

          {/* Détails d'usage */}
          {!usageData.usage.needsReauthentication && (
            <div className="py-2 space-y-3">
              {/* Session */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground">{t('common:usage.session')}</span>
                  <span className={`text-xs font-semibold ${sessionColorClass}`}>
                    {Math.round(sessionPercent)}%
                  </span>
                </div>
                <div className="w-full bg-muted rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all ${getBarColorClass(sessionPercent)}`}
                    style={{ width: `${Math.min(sessionPercent, 100)}%` }}
                  />
                </div>
                {sessionResetTime && (
                  <p className="text-[9px] text-muted-foreground">
                    {t('common:usage.resetsIn', { time: sessionResetTime })}
                  </p>
                )}
              </div>

              {/* Weekly */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground">{t('common:usage.weekly')}</span>
                  <span className={`text-xs font-semibold ${weeklyColorClass}`}>
                    {Math.round(weeklyPercent)}%
                  </span>
                </div>
                <div className="w-full bg-muted rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all ${getBarColorClass(weeklyPercent)}`}
                    style={{ width: `${Math.min(weeklyPercent, 100)}%` }}
                  />
                </div>
                {weeklyResetTime && (
                  <p className="text-[9px] text-muted-foreground">
                    {t('common:usage.resetsIn', { time: weeklyResetTime })}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Footer avec compte actif */}
          <button
            type="button"
            onClick={handleOpenAccounts}
            className="w-full pt-3 border-t flex items-center gap-2.5 hover:bg-muted/50 -mx-3 px-3 pb-2 transition-colors cursor-pointer group"
          >
            <div className="relative">
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-primary/10">
                <span className="text-xs font-semibold text-primary">
                  {getInitials(credential?.credentials?.profileName || usageData.profileName || 'Unknown')}
                </span>
              </div>
              {usageData.usage.needsReauthentication && (
                <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-background" />
              )}
            </div>

            <div className="flex-1 min-w-0 text-left">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-muted-foreground font-medium">
                  {t('common:usage.activeAccount')}
                </span>
                {usageData.usage.needsReauthentication && (
                  <span className="text-[9px] px-1.5 py-0.5 bg-red-500/10 text-destructive rounded font-semibold">
                    {t('common:usage.needsReauth')}
                  </span>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground truncate">
                {credential?.credentials?.profileName || usageData.profileName || 'Unknown Account'}
              </p>
            </div>
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

/**
 * Obtenir la classe de couleur pour les barres d'usage
 */
function getBarColorClass(percent: number): string {
  if (percent >= THRESHOLD_CRITICAL) return 'bg-red-500';
  if (percent >= THRESHOLD_WARNING) return 'bg-orange-500';
  if (percent >= THRESHOLD_ELEVATED) return 'bg-yellow-500';
  return 'bg-green-500';
}

export default UsageIndicatorDumb;
