import { useTranslation } from 'react-i18next';
import { useSelfHealingStore } from '@/stores/self-healing-store';
import { IncidentCard } from './IncidentCard';
import type { IncidentSource } from '@shared/types/self-healing';

interface ProductionTabProps {
  readonly projectPath: string;
}

const APM_SOURCES: Array<{ source: IncidentSource; label: string; icon: string }> = [
  { source: 'sentry', label: 'Sentry', icon: '\uD83D\uDC1B' },
  { source: 'datadog', label: 'Datadog', icon: '\uD83D\uDC15' },
  { source: 'cloudwatch', label: 'CloudWatch', icon: '\u2601\uFE0F' },
  { source: 'new_relic', label: 'New Relic', icon: '\uD83D\uDC8E' },
  { source: 'pagerduty', label: 'PagerDuty', icon: '\uD83D\uDCDF' },
];

export function ProductionTab({ projectPath }: ProductionTabProps) {
  const { t } = useTranslation(['selfHealing']);
  const {
    incidents,
    productionConfig,
    setProductionConfig,
    triggerFix,
    dismissIncident,
    retryIncident,
  } = useSelfHealingStore();

  const productionIncidents = incidents.filter((i) => i.mode === 'production');

  return (
    <div className="space-y-4">
      {/* Config panel */}
      <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] p-4">
        <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3">
          {t('selfHealing:productionConfig')}
        </h3>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={productionConfig.enabled}
              onChange={(e) => setProductionConfig(projectPath, { enabled: e.target.checked })}
              className="rounded"
            />
            {t('selfHealing:productionEnabled')}
          </label>
          <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={productionConfig.autoAnalyze}
              onChange={(e) => setProductionConfig(projectPath, { autoAnalyze: e.target.checked })}
              className="rounded"
            />
            {t('selfHealing:autoAnalyze')}
          </label>
          <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={productionConfig.autoFix}
              onChange={(e) => setProductionConfig(projectPath, { autoFix: e.target.checked })}
              className="rounded"
            />
            {t('selfHealing:autoFixProduction')}
          </label>
        </div>
      </div>

      {/* Connected sources panel */}
      <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] p-4">
        <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3">
          {t('selfHealing:connectedSources')}
        </h3>
        <div className="grid grid-cols-5 gap-2">
          {APM_SOURCES.map(({ source, label, icon }) => {
            const isConnected = productionConfig.connectedSources.includes(source);
            return (
              <button
                key={source}
                type="button"
                className={`flex flex-col items-center gap-1 p-3 rounded-lg border transition-colors ${
                  isConnected
                    ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10'
                    : 'border-[var(--border-primary)] bg-[var(--bg-tertiary)] hover:border-[var(--accent-primary)]/50'
                }`}
              >
                <span className="text-xl">{icon}</span>
                <span className="text-xs text-[var(--text-secondary)]">{label}</span>
                <span className={`text-xs ${isConnected ? 'text-green-400' : 'text-[var(--text-tertiary)]'}`}>
                  {isConnected ? t('selfHealing:connected') : t('selfHealing:disconnected')}
                </span>
              </button>
            );
          })}
        </div>
        <p className="text-xs text-[var(--text-tertiary)] mt-3">
          {t('selfHealing:productionDescription')}
        </p>
      </div>

      {/* Live incidents */}
      <div>
        <h3 className="text-sm font-medium text-[var(--text-primary)] mb-2">
          {t('selfHealing:liveIncidents')} ({productionIncidents.length})
        </h3>
        {productionIncidents.length === 0 ? (
          <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] p-6 text-center">
            <p className="text-sm text-[var(--text-secondary)]">
              {t('selfHealing:noProductionIncidents')}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {productionIncidents.map((incident) => (
              <IncidentCard
                key={incident.id}
                incident={incident}
                onTriggerFix={(id) => triggerFix(projectPath, id)}
                onDismiss={(id) => dismissIncident(projectPath, id)}
                onRetry={(id) => retryIncident(projectPath, id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
