import { useTranslation } from 'react-i18next';
import { useBrowserAgentStore } from '@/stores/browser-agent-store';
import { useState } from 'react';

interface TestRunnerTabProps {
  readonly projectPath: string;
}

export function TestRunnerTab({ projectPath }: TestRunnerTabProps) {
  const { t } = useTranslation(['browserAgent']);
  const { recentTestRun, isRunningTests, runTests } = useBrowserAgentStore();
  const [expandedTest, setExpandedTest] = useState<string | null>(null);

  const handleRunTests = () => {
    runTests(projectPath);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Run button */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={handleRunTests}
          disabled={isRunningTests}
          className="px-4 py-2 rounded-md bg-[var(--accent-primary)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isRunningTests && (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          )}
          {isRunningTests ? t('browserAgent:tests.running') : t('browserAgent:tests.runAll')}
        </button>

        {/* Summary */}
        {recentTestRun && (
          <div className="text-sm text-[var(--text-secondary)]">
            {t('browserAgent:tests.summary', {
              passed: recentTestRun.passed,
              failed: recentTestRun.failed,
              skipped: recentTestRun.skipped,
            })}
            <span className="ml-2 text-xs text-[var(--text-tertiary)]">
              ({(recentTestRun.durationMs / 1000).toFixed(1)}s)
            </span>
          </div>
        )}
      </div>

      {/* Results */}
      {!recentTestRun && !isRunningTests && (
        <div className="flex items-center justify-center h-48">
          <p className="text-sm text-[var(--text-tertiary)]">
            {t('browserAgent:tests.noResults')}
          </p>
        </div>
      )}

      {recentTestRun && (
        <div className="space-y-1">
          {recentTestRun.results.map((result) => {
            const isExpanded = expandedTest === `${result.path}:${result.name}`;
            const statusConfig = getStatusConfig(result.status);

            return (
              <div key={`${result.path}:${result.name}`}>
                <button
                  type="button"
                  onClick={() =>
                    setExpandedTest(isExpanded ? null : `${result.path}:${result.name}`)
                  }
                  className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-[var(--bg-hover)] text-left"
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-sm ${statusConfig.color}`}>
                      {statusConfig.icon}
                    </span>
                    <span className="text-sm text-[var(--text-primary)]">{result.name}</span>
                    <span className="text-xs text-[var(--text-tertiary)]">{result.path}</span>
                  </div>
                  <span className="text-xs text-[var(--text-tertiary)]">
                    {result.durationMs.toFixed(0)}ms
                  </span>
                </button>

                {isExpanded && result.errorMessage && (
                  <div className="ml-8 mt-1 mb-2 p-3 rounded bg-red-500/5 border border-red-500/20">
                    <p className="text-xs font-medium text-red-400 mb-1">
                      {t('browserAgent:tests.errorDetails')}
                    </p>
                    <pre className="text-xs text-[var(--text-secondary)] whitespace-pre-wrap font-mono">
                      {result.errorMessage}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function getStatusConfig(status: string): { icon: string; color: string } {
  switch (status) {
    case 'passed':
      return { icon: '\u2713', color: 'text-green-400' };
    case 'failed':
      return { icon: '\u2717', color: 'text-red-400' };
    case 'skipped':
      return { icon: '\u2500', color: 'text-yellow-400' };
    case 'error':
      return { icon: '!', color: 'text-red-500' };
    default:
      return { icon: '?', color: 'text-[var(--text-tertiary)]' };
  }
}
