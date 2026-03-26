import { AlertCircle, TrendingUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { UsageSnapshot } from '@shared/types';

interface CopilotUsageContentProps {
  readonly usage: UsageSnapshot;
}

export function CopilotUsageContent({ usage }: CopilotUsageContentProps) {
  return (
    <div className="py-2 space-y-3">
      {renderCopilotErrorState(usage)}
    </div>
  );
}

function renderCopilotErrorState(usage: UsageSnapshot) {
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  const error = (usage as any).error;

  if (error === 'INSUFFICIENT_PERMISSIONS') {
    return <CopilotInsufficientPermissions usage={usage} />;
  }

  if (error === 'BACKEND_UNAVAILABLE') {
    return <CopilotBackendUnavailable />;
  }

  return <CopilotMetrics usage={usage} />;
}

interface CopilotInsufficientPermissionsProps {
  readonly usage: UsageSnapshot;
}

function CopilotInsufficientPermissions({ usage }: CopilotInsufficientPermissionsProps) {
  const { t } = useTranslation(['common']);

  return (
    <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-orange-500/10 border border-orange-500/20">
      <AlertCircle className="h-4 w-4 text-orange-500 shrink-0 mt-0.5" />
      <div className="space-y-1">
        <p className="text-xs font-medium text-orange-500">
          {t('common:usage.copilotInsuffPermissions')}
        </p>
        <p className="text-[10px] text-muted-foreground leading-relaxed">
          {/* biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly */}
          {(usage as any).errorMessage || t('common:usage.copilotInsuffPermissionsDesc')}
        </p>
        <div className="text-[10px] text-muted-foreground">
          <strong>{t('common:usage.copilotSuggestionsLabel')}:</strong>
          <ul className="list-disc list-inside space-y-0.5 mt-1">
            <li>{t('common:usage.copilotRunCmd')} <code className="bg-muted px-1 rounded">gh auth refresh -h github.com -s admin:org</code></li>
            <li>{t('common:usage.copilotMustBeAdmin')}</li>
            <li>{t('common:usage.copilotContactAdmin')}</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function CopilotBackendUnavailable() {
  const { t } = useTranslation(['common']);

  return (
    <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
      <AlertCircle className="h-4 w-4 text-yellow-500 shrink-0 mt-0.5" />
      <div className="space-y-1">
        <p className="text-xs font-medium text-yellow-500">
          {t('common:usage.copilotBackendUnavailable')}
        </p>
        <p className="text-[10px] text-muted-foreground leading-relaxed">
          {t('common:usage.copilotBackendUnavailableDesc')}
        </p>
      </div>
    </div>
  );
}

interface CopilotMetricsProps {
  readonly usage: UsageSnapshot;
}

function CopilotMetrics({ usage }: CopilotMetricsProps) {
  const { t } = useTranslation(['common']);

  return (
    <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20">
      <TrendingUp className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
      <div className="space-y-1">
        <p className="text-xs font-medium text-blue-500">
          {t('common:usage.copilotMetricsTitle')}
        </p>
        <p className="text-[10px] text-muted-foreground leading-relaxed">
          {t('common:usage.copilotMetricsDesc')}
        </p>
        {usage.copilotUsageDetails && (
          <div className="mt-2 space-y-1">
            {usage.copilotUsageDetails.suggestionsCount !== undefined && (
              <div className="flex justify-between text-[10px]">
                <span>{t('common:usage.copilotSuggestionsLabel')}:</span>
                <span className="font-mono">{usage.copilotUsageDetails.suggestionsCount}</span>
              </div>
            )}
            {usage.copilotUsageDetails.acceptancesCount !== undefined && (
              <div className="flex justify-between text-[10px]">
                <span>{t('common:usage.copilotAcceptancesLabel')}:</span>
                <span className="font-mono">{usage.copilotUsageDetails.acceptancesCount}</span>
              </div>
            )}
            {usage.copilotUsageDetails.acceptanceRate !== undefined && (
              <div className="flex justify-between text-[10px]">
                <span>{t('common:usage.copilotAcceptanceRateLabel')}:</span>
                <span className="font-mono">{usage.copilotUsageDetails.acceptanceRate.toFixed(1)}%</span>
              </div>
            )}
            {usage.copilotUsageDetails.totalTokens !== undefined && usage.copilotUsageDetails.totalTokens > 0 && (
              <div className="flex justify-between text-[10px]">
                <span>{t('common:usage.copilotTokensUsedLabel')}:</span>
                <span className="font-mono">{usage.copilotUsageDetails.totalTokens}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
