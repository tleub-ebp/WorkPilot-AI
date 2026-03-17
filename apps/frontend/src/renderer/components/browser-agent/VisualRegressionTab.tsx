import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useBrowserAgentStore } from '@/stores/browser-agent-store';

interface VisualRegressionTabProps {
  readonly projectPath: string;
}

export function VisualRegressionTab({ projectPath }: VisualRegressionTabProps) {
  const { t } = useTranslation(['browserAgent']);
  const {
    baselines,
    comparisons,
    screenshots,
    isComparing,
    isLoading,
    setBaseline,
    compareScreenshot,
    deleteBaseline,
  } = useBrowserAgentStore();

  const [, setSelectedComparison] = useState<string | null>(null);

  const handleSetBaseline = async (name: string) => {
    // Find the most recent screenshot with this name
    const screenshot = screenshots.find((s) => s.name === name);
    await setBaseline(projectPath, name, screenshot?.path);
  };

  const handleCompare = async (name: string) => {
    await compareScreenshot(projectPath, name);
    setSelectedComparison(name);
  };

  if (baselines.length === 0 && screenshots.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-sm text-[var(--text-tertiary)]">
          {t('browserAgent:regression.noBaselines')}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Screenshots available to set as baseline */}
      {screenshots.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[var(--text-primary)] mb-2">
            {t('browserAgent:stats.screenshots')} ({screenshots.length})
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {screenshots.slice(0, 10).map((screenshot) => {
              const hasBaseline = baselines.some((b) => b.name === screenshot.name);
              return (
                <div
                  key={screenshot.path}
                  className="p-3 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[var(--text-primary)] truncate">
                      {screenshot.name}
                    </span>
                    <span className="text-xs text-[var(--text-tertiary)]">
                      {screenshot.width}x{screenshot.height}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {!hasBaseline && (
                      <button
                        type="button"
                        onClick={() => handleSetBaseline(screenshot.name)}
                        disabled={isLoading}
                        className="px-3 py-1 text-xs rounded bg-[var(--accent-primary)] text-white hover:opacity-90 disabled:opacity-50"
                      >
                        {t('browserAgent:regression.setBaseline')}
                      </button>
                    )}
                    {hasBaseline && (
                      <button
                        type="button"
                        onClick={() => handleCompare(screenshot.name)}
                        disabled={isComparing}
                        className="px-3 py-1 text-xs rounded border border-[var(--accent-primary)] text-[var(--accent-primary)] hover:bg-[var(--accent-primary)] hover:text-white disabled:opacity-50"
                      >
                        {isComparing ? t('browserAgent:regression.comparing') : t('browserAgent:regression.compare')}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Baselines */}
      {baselines.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[var(--text-primary)] mb-2">
            {t('browserAgent:regression.baseline')}s ({baselines.length})
          </h3>
          <div className="space-y-2">
            {baselines.map((baseline) => (
              <div
                key={baseline.name}
                className="flex items-center justify-between p-3 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded bg-[var(--bg-tertiary)] flex items-center justify-center text-xs">
                    {baseline.width}x{baseline.height}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)]">{baseline.name}</p>
                    <p className="text-xs text-[var(--text-tertiary)]">
                      {new Date(baseline.createdAt).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleCompare(baseline.name)}
                    disabled={isComparing}
                    className="px-3 py-1 text-xs rounded border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] disabled:opacity-50"
                  >
                    {t('browserAgent:regression.compare')}
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteBaseline(projectPath, baseline.name)}
                    disabled={isLoading}
                    className="px-3 py-1 text-xs rounded border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                  >
                    {t('browserAgent:regression.deleteBaseline')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Comparison results */}
      {comparisons.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[var(--text-primary)] mb-2">
            {t('browserAgent:regression.compare')} Results
          </h3>
          <div className="space-y-3">
            {comparisons.map((comparison) => (
              <div
                key={comparison.name}
                className={`p-4 rounded-lg border ${
                  comparison.passed
                    ? 'border-green-500/30 bg-green-500/5'
                    : 'border-red-500/30 bg-red-500/5'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-[var(--text-primary)]">
                    {comparison.name}
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        comparison.passed
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}
                    >
                      {comparison.passed
                        ? t('browserAgent:regression.passed')
                        : t('browserAgent:regression.failed')}
                    </span>
                    <span
                      className={`text-sm font-mono font-bold ${
                        comparison.matchPercentage >= 95
                          ? 'text-green-400'
                          : comparison.matchPercentage >= 85
                            ? 'text-yellow-400'
                            : 'text-red-400'
                      }`}
                    >
                      {comparison.matchPercentage}%
                    </span>
                  </div>
                </div>
                <div className="flex gap-4 text-xs text-[var(--text-tertiary)]">
                  <span>
                    {t('browserAgent:regression.diffPixels')}: {comparison.diffPixels.toLocaleString()}
                  </span>
                  <span>
                    {t('browserAgent:regression.threshold')}: {comparison.threshold}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
