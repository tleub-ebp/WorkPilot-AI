import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useBrowserAgentStore } from '@/stores/browser-agent-store';
import { useProjectStore } from '@/stores/project-store';
import { BrowserTab } from './BrowserTab';
import { VisualRegressionTab } from './VisualRegressionTab';
import { TestRunnerTab } from './TestRunnerTab';
import type { BrowserAgentTab } from '@shared/types/browser-agent';

const TABS: Array<{ id: BrowserAgentTab; icon: string; labelKey: string }> = [
  { id: 'browser', icon: '\uD83C\uDF10', labelKey: 'browserAgent:tabs.browser' },
  { id: 'visual-regression', icon: '\uD83D\uDDBC\uFE0F', labelKey: 'browserAgent:tabs.visualRegression' },
  { id: 'test-runner', icon: '\uD83E\uDDEA', labelKey: 'browserAgent:tabs.testRunner' },
];

export function BrowserAgentDashboard() {
  const { t } = useTranslation(['browserAgent', 'common']);
  const { activeTab, setActiveTab, stats, isLoading, error, fetchDashboard } =
    useBrowserAgentStore();
  const selectedProject = useProjectStore((s) => s.getSelectedProject?.());
  const projectPath = selectedProject?.path || '';

  useEffect(() => {
    if (projectPath) {
      fetchDashboard(projectPath);
    }
  }, [projectPath, fetchDashboard]);

  if (!projectPath) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm text-[var(--text-tertiary)]">
          {t('browserAgent:errors.noProject')}
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[var(--border-primary)] bg-[var(--bg-primary)]">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-[var(--text-primary)]">
              {t('browserAgent:title')}
            </h1>
            <p className="text-xs text-[var(--text-tertiary)] mt-0.5">
              {t('browserAgent:subtitle')}
            </p>
          </div>
        </div>

        {/* Stats summary */}
        <div className="grid grid-cols-4 gap-3 mt-3">
          <StatCard
            label={t('browserAgent:stats.totalTests')}
            value={stats.totalTests}
          />
          <StatCard
            label={t('browserAgent:stats.passRate')}
            value={`${stats.passRate.toFixed(0)}%`}
            variant={stats.passRate >= 80 ? 'success' : stats.passRate > 0 ? 'warning' : 'default'}
          />
          <StatCard
            label={t('browserAgent:stats.screenshots')}
            value={stats.screenshotsCaptured}
          />
          <StatCard
            label={t('browserAgent:stats.regressions')}
            value={stats.regressionsDetected}
            variant={stats.regressionsDetected > 0 ? 'warning' : 'default'}
          />
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-[var(--border-primary)] bg-[var(--bg-primary)] px-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{t(tab.labelKey)}</span>
          </button>
        ))}
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-6 py-2 bg-red-500/10 border-b border-red-500/20">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-6 h-6 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {activeTab === 'browser' && <BrowserTab projectPath={projectPath} />}
            {activeTab === 'visual-regression' && (
              <VisualRegressionTab projectPath={projectPath} />
            )}
            {activeTab === 'test-runner' && <TestRunnerTab projectPath={projectPath} />}
          </>
        )}
      </div>
    </div>
  );
}

// ── StatCard component ──────────────────────────────────────

function StatCard({
  label,
  value,
  variant = 'default',
}: {
  readonly label: string;
  readonly value: string | number;
  readonly variant?: 'default' | 'success' | 'warning';
}) {
  const colorClass =
    variant === 'success'
      ? 'text-green-400'
      : variant === 'warning'
        ? 'text-yellow-400'
        : 'text-[var(--text-primary)]';

  return (
    <div className="px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-primary)]">
      <p className="text-xs text-[var(--text-tertiary)]">{label}</p>
      <p className={`text-lg font-semibold ${colorClass}`}>{value}</p>
    </div>
  );
}
