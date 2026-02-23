/**
 * Agnostic Usage Converter - Converts provider-specific usage data to agnostic format
 */

import { 
  AgnosticUsageData, 
  BaseUsageMetrics, 
  ProviderSpecificDetails, 
  UsageError,
  getProviderConfig 
} from '@shared/types/agnostic-usage';
import type { UsageSnapshot } from '@shared/types/agent';

/**
 * Convert UsageSnapshot to AgnosticUsageData
 */
export function convertToAgnosticUsage(snapshot: UsageSnapshot): AgnosticUsageData {
  const providerConfig = getProviderConfig(snapshot.providerName || 'generic');
  
  // Base metrics conversion
  const metrics: BaseUsageMetrics = {
    sessionPercent: snapshot.sessionPercent,
    periodicPercent: snapshot.weeklyPercent,
    sessionResetTime: snapshot.sessionResetTime,
    periodicResetTime: snapshot.weeklyResetTime,
    sessionResetTimestamp: snapshot.sessionResetTimestamp,
    periodicResetTimestamp: snapshot.weeklyResetTimestamp,
    sessionUsageValue: snapshot.sessionUsageValue,
    sessionUsageLimit: snapshot.sessionUsageLimit,
    periodicUsageValue: snapshot.weeklyUsageValue,
    periodicUsageLimit: snapshot.weeklyUsageLimit
  };

  // Provider-specific details conversion
  const details: ProviderSpecificDetails = {};
  
  if (snapshot.providerName === 'anthropic') {
    details.anthropic = {
      subscriptionType: (snapshot as any).subscriptionType,
      rateLimitTier: (snapshot as any).rateLimitTier,
      opusUsagePercent: (snapshot as any).opusUsagePercent
    };
  } else if (snapshot.providerName === 'openai') {
    details.openai = snapshot.openaiUsageDetails || {};
  } else if (snapshot.providerName === 'copilot') {
    details.copilot = snapshot.copilotUsageDetails || {};
  } else {
    // Generic provider - store any extra data
    details.generic = { ...(snapshot as any) };
  }

  // Error handling
  let error: UsageError | undefined;
  if ((snapshot as any).error) {
    error = {
      code: (snapshot as any).error,
      message: (snapshot as any).errorMessage || 'Unknown error occurred',
      suggestions: (snapshot as any).suggestions || [],
      provider: snapshot.providerName,
      requiresAction: true,
      actionType: getActionTypeForError((snapshot as any).error)
    };
  }

  return {
    provider: snapshot.providerName || 'generic',
    profileId: snapshot.profileId,
    profileName: snapshot.profileName,
    profileEmail: snapshot.profileEmail,
    metrics,
    details,
    error,
    isAuthenticated: !(snapshot as any).isRateLimited || snapshot.needsReauthentication !== true,
    needsReauthentication: snapshot.needsReauthentication || false,
    isRateLimited: (snapshot as any).isRateLimited || false,
    rateLimitType: snapshot.limitType === 'session' ? 'session' : 'periodic',
    fetchedAt: snapshot.fetchedAt,
    usageWindows: snapshot.usageWindows ? {
      sessionWindowLabel: snapshot.usageWindows.sessionWindowLabel,
      periodicWindowLabel: snapshot.usageWindows.weeklyWindowLabel
    } : undefined
  };
}

/**
 * Convert backend error to UsageError
 */
export function convertBackendError(provider: string, backendError: any): UsageError {
  const errorCode = backendError.error || backendError.code || 'UNKNOWN_ERROR';
  
  return {
    code: errorCode,
    message: backendError.message || backendError.errorMessage || 'Unknown error occurred',
    suggestions: backendError.suggestions || [],
    provider,
    requiresAction: true,
    actionType: getActionTypeForError(errorCode)
  };
}

/**
 * Determine action type based on error code
 */
function getActionTypeForError(errorCode: string): 'reauth' | 'permission' | 'configuration' | 'retry' {
  if (errorCode.includes('INSUFFICIENT_PERMISSIONS') || errorCode.includes('admin:org')) {
    return 'permission';
  }
  if (errorCode.includes('NEEDS_REAUTHENTICATION') || errorCode.includes('AUTH_FAILED')) {
    return 'reauth';
  }
  if (errorCode.includes('BACKEND_UNAVAILABLE') || errorCode.includes('NETWORK_ERROR')) {
    return 'retry';
  }
  if (errorCode.includes('CONFIGURATION') || errorCode.includes('INVALID_API_KEY')) {
    return 'configuration';
  }
  return 'retry';
}

/**
 * Format usage value based on provider and display format
 */
export function formatUsageValue(
  usageData: AgnosticUsageData, 
  format?: 'percentage' | 'tokens' | 'cost' | 'custom'
): string {
  const providerConfig = getProviderConfig(usageData.provider);
  const displayFormat = format || providerConfig.defaultDisplayFormat;
  
  switch (displayFormat) {
    case 'percentage':
      return `${Math.round(usageData.metrics.periodicPercent)}%`;
      
    case 'tokens':
      if (usageData.details?.copilot?.totalTokens) {
        return formatCompactNumber(usageData.details.copilot.totalTokens) + 'T';
      }
      if (usageData.metrics.periodicUsageValue) {
        return formatCompactNumber(usageData.metrics.periodicUsageValue);
      }
      return '0T';
      
    case 'cost':
      if (usageData.details?.openai?.estimatedCost) {
        return `$${usageData.details.openai.estimatedCost.toFixed(2)}`;
      }
      if (usageData.metrics.periodicUsageValue) {
        return `$${usageData.metrics.periodicUsageValue.toFixed(2)}`;
      }
      return '$0.00';
      
    case 'custom':
      return formatCustomValue(usageData);
      
    default:
      return `${Math.round(usageData.metrics.periodicPercent)}%`;
  }
}

/**
 * Format number with compact notation
 */
function formatCompactNumber(value: number): string {
  if (typeof Intl !== 'undefined' && Intl.NumberFormat) {
    try {
      return new Intl.NumberFormat('en-US', {
        notation: 'compact',
        compactDisplay: 'short',
        maximumFractionDigits: 1
      }).format(value);
    } catch {
      // Fall back to simple formatting
    }
  }
  
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toString();
}

/**
 * Custom formatting for specific providers
 */
function formatCustomValue(usageData: AgnosticUsageData): string {
  switch (usageData.provider) {
    case 'anthropic':
      if (usageData.details?.anthropic?.subscriptionType) {
        const subType = usageData.details.anthropic.subscriptionType;
        return `${Math.round(usageData.metrics.periodicPercent)}% (${subType})`;
      }
      return `${Math.round(usageData.metrics.periodicPercent)}%`;
      
    case 'openai':
      if (usageData.details?.openai?.cost?.data?.[0]) {
        const costData = usageData.details.openai.cost.data[0];
        return `$${costData.cost_usd?.toFixed(2) || '0.00'}`;
      }
      return `$${(usageData.metrics.periodicUsageValue || 0).toFixed(2)}`;
      
    case 'copilot':
      if (usageData.details?.copilot?.acceptanceRate) {
        return `${usageData.details.copilot.acceptanceRate.toFixed(1)}%`;
      }
      return formatCompactNumber(usageData.details?.copilot?.totalTokens || 0) + 'T';
      
    default:
      return `${Math.round(usageData.metrics.periodicPercent)}%`;
  }
}

/**
 * Get display color class based on usage percentage
 */
export function getUsageColorClass(percent: number): string {
  if (percent >= 95) return 'text-red-500';
  if (percent >= 91) return 'text-orange-500';
  if (percent >= 71) return 'text-yellow-500';
  return 'text-green-500';
}

/**
 * Get badge color classes based on usage percentage
 */
export function getBadgeColorClasses(percent: number, needsReauth: boolean = false): string {
  if (needsReauth) return 'text-red-500 bg-red-500/10 border-red-500/20';
  if (percent >= 95) return 'text-red-500 bg-red-500/10 border-red-500/20';
  if (percent >= 91) return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
  if (percent >= 71) return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
  return 'text-green-500 bg-green-500/10 border-green-500/20';
}

/**
 * Get gradient background class based on usage percentage
 */
export function getGradientClass(percent: number): string {
  if (percent >= 95) return 'bg-gradient-to-r from-red-600 to-red-500';
  if (percent >= 91) return 'bg-gradient-to-r from-orange-600 to-orange-500';
  if (percent >= 71) return 'bg-gradient-to-r from-yellow-600 to-yellow-500';
  return 'bg-gradient-to-r from-green-600 to-green-500';
}
