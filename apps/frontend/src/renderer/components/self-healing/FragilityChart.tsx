import { useTranslation } from 'react-i18next';
import type { FragilityReport } from '@shared/types/self-healing';

interface FragilityChartProps {
  readonly reports: FragilityReport[];
  readonly maxItems?: number;
}

function getRiskColor(score: number): string {
  if (score >= 80) return 'bg-red-500';
  if (score >= 60) return 'bg-orange-500';
  if (score >= 40) return 'bg-yellow-500';
  return 'bg-blue-500';
}

function getRiskBgColor(score: number): string {
  if (score >= 80) return 'bg-red-500/10';
  if (score >= 60) return 'bg-orange-500/10';
  if (score >= 40) return 'bg-yellow-500/10';
  return 'bg-blue-500/10';
}

export function FragilityChart({ reports, maxItems = 15 }: FragilityChartProps) {
  const { t } = useTranslation(['selfHealing']);
  const displayReports = reports.slice(0, maxItems);

  if (displayReports.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] p-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">
          {t('selfHealing:noFragilityData')}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] p-4">
      <h4 className="text-sm font-medium text-[var(--text-primary)] mb-3">
        {t('selfHealing:fragilityRiskMap')}
      </h4>
      <div className="space-y-2">
        {displayReports.map((report) => {
          const fileName = report.file_path.split('/').pop() || report.file_path;
          const dirPath = report.file_path.split('/').slice(0, -1).join('/');

          return (
            <div key={report.file_path} className={`rounded p-2 ${getRiskBgColor(report.risk_score)}`}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex-1 min-w-0 mr-2">
                  <span className="text-xs font-mono text-[var(--text-primary)] truncate block">
                    {fileName}
                  </span>
                  {dirPath && (
                    <span className="text-xs font-mono text-[var(--text-tertiary)] truncate block">
                      {dirPath}/
                    </span>
                  )}
                </div>
                <span className="text-xs font-semibold text-[var(--text-primary)] whitespace-nowrap">
                  {report.risk_score.toFixed(0)}%
                </span>
              </div>
              {/* Risk bar */}
              <div className="w-full bg-[var(--bg-tertiary)] rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all ${getRiskColor(report.risk_score)}`}
                  style={{ width: `${Math.min(report.risk_score, 100)}%` }}
                />
              </div>
              {/* Metrics */}
              <div className="flex gap-3 mt-1 text-xs text-[var(--text-tertiary)]">
                <span>{t('selfHealing:complexity')}: {report.cyclomatic_complexity.toFixed(0)}</span>
                <span>{t('selfHealing:churn')}: {report.git_churn_count}</span>
                <span>{t('selfHealing:coverage')}: {report.test_coverage_percent.toFixed(0)}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
