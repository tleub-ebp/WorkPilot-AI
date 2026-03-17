import { useTranslation } from 'react-i18next';
import type { Incident } from '@shared/types/self-healing';

interface IncidentCardProps {
  readonly incident: Incident;
  readonly onTriggerFix?: (id: string) => void;
  readonly onDismiss?: (id: string) => void;
  readonly onRetry?: (id: string) => void;
}

const severityColors: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  info: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

const statusIcons: Record<string, string> = {
  pending: '\u23F3',
  analyzing: '\uD83D\uDD0D',
  fixing: '\uD83D\uDD27',
  qa_running: '\uD83E\uDDEA',
  pr_created: '\uD83D\uDD17',
  resolved: '\u2705',
  escalated: '\u26A0\uFE0F',
  failed: '\u274C',
};

export function IncidentCard({ incident, onTriggerFix, onDismiss, onRetry }: IncidentCardProps) {
  const { t } = useTranslation(['selfHealing', 'common']);
  const isActionable = ['pending', 'failed', 'escalated'].includes(incident.status);

  return (
    <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-base">{statusIcons[incident.status] || '\u2753'}</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full border ${severityColors[incident.severity] || severityColors.info}`}
            >
              {incident.severity.toUpperCase()}
            </span>
            <span className="text-xs text-[var(--text-tertiary)]">
              [{incident.mode}]
            </span>
          </div>
          <h4 className="text-sm font-medium text-[var(--text-primary)] truncate">
            {incident.title}
          </h4>
          <p className="text-xs text-[var(--text-secondary)] mt-1 line-clamp-2">
            {incident.description}
          </p>
          {incident.affected_files.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {incident.affected_files.slice(0, 3).map((file) => (
                <span
                  key={file}
                  className="text-xs px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] font-mono"
                >
                  {file.split('/').pop()}
                </span>
              ))}
              {incident.affected_files.length > 3 && (
                <span className="text-xs text-[var(--text-tertiary)]">
                  +{incident.affected_files.length - 3}
                </span>
              )}
            </div>
          )}
          {incident.fix_pr_url && (
            <a
              href={incident.fix_pr_url}
              className="text-xs text-[var(--accent-primary)] hover:underline mt-1 inline-block"
              target="_blank"
              rel="noopener noreferrer"
            >
              {t('selfHealing:viewPR')}
            </a>
          )}
        </div>

        {isActionable && (
          <div className="flex flex-col gap-1">
            {incident.status === 'pending' && onTriggerFix && (
              <button
                type="button"
                onClick={() => onTriggerFix(incident.id)}
                className="text-xs px-2 py-1 rounded bg-[var(--accent-primary)] text-white hover:opacity-80"
              >
                {t('selfHealing:fix')}
              </button>
            )}
            {incident.status === 'failed' && onRetry && (
              <button
                type="button"
                onClick={() => onRetry(incident.id)}
                className="text-xs px-2 py-1 rounded bg-[var(--accent-primary)] text-white hover:opacity-80"
              >
                {t('selfHealing:retry')}
              </button>
            )}
            {onDismiss && (
              <button
                type="button"
                onClick={() => onDismiss(incident.id)}
                className="text-xs px-2 py-1 rounded border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
              >
                {t('selfHealing:dismiss')}
              </button>
            )}
          </div>
        )}
      </div>
      <div className="mt-2 text-xs text-[var(--text-tertiary)]">
        {new Date(incident.created_at).toLocaleString()}
      </div>
    </div>
  );
}
