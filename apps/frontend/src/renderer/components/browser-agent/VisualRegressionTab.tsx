import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useBrowserAgentStore } from '@/stores/browser-agent-store';
import {
  ImageIcon,
  Layers,
  Trash2,
  GitCompareArrows,
  CheckCircle2,
  XCircle,
  Loader2,
  ScanEye,
  Bookmark,
} from 'lucide-react';

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
    const screenshot = screenshots.find((s) => s.name === name);
    await setBaseline(projectPath, name, screenshot?.path);
  };

  const handleCompare = async (name: string) => {
    await compareScreenshot(projectPath, name);
    setSelectedComparison(name);
  };

  // Empty state
  if (baselines.length === 0 && screenshots.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-500/15 to-pink-500/15 border border-purple-500/20 flex items-center justify-center shadow-lg shadow-purple-500/5">
          <ScanEye className="w-10 h-10 text-purple-400/70" />
        </div>
        <div className="text-center max-w-xs">
          <p className="text-sm font-medium text-[var(--text-secondary)] mb-1">
            {t('browserAgent:regression.noBaselinesTitle')}
          </p>
          <p className="text-xs text-[var(--text-tertiary)] leading-relaxed">
            {t('browserAgent:regression.noBaselines')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Screenshots available to set as baseline */}
      {screenshots.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <ImageIcon className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-medium text-[var(--text-primary)]">
              {t('browserAgent:stats.screenshots')}
            </h3>
            <span className="text-xs text-cyan-400 px-1.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20">
              {screenshots.length}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {screenshots.slice(0, 10).map((screenshot) => {
              const hasBaseline = baselines.some((b) => b.name === screenshot.name);
              return (
                <div
                  key={screenshot.path}
                  className="group p-3 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] hover:border-cyan-500/30 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <ImageIcon className="w-3.5 h-3.5 text-cyan-400/70 shrink-0" />
                      <span className="text-sm font-medium text-[var(--text-primary)] truncate">
                        {screenshot.name}
                      </span>
                    </div>
                    <span className="text-[11px] text-[var(--text-tertiary)] font-mono shrink-0 ml-2">
                      {screenshot.width}x{screenshot.height}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {!hasBaseline && (
                      <button
                        type="button"
                        onClick={() => handleSetBaseline(screenshot.name)}
                        disabled={isLoading}
                        className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md bg-amber-500 text-white hover:bg-amber-400 disabled:opacity-50 transition-colors"
                      >
                        <Bookmark className="w-3 h-3" />
                        {t('browserAgent:regression.setBaseline')}
                      </button>
                    )}
                    {hasBaseline && (
                      <button
                        type="button"
                        onClick={() => handleCompare(screenshot.name)}
                        disabled={isComparing}
                        className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md border border-purple-500/40 text-purple-400 hover:bg-purple-500/10 disabled:opacity-50 transition-colors"
                      >
                        {isComparing ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <GitCompareArrows className="w-3 h-3" />
                        )}
                        {isComparing ? t('browserAgent:regression.comparing') : t('browserAgent:regression.compare')}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Baselines */}
      {baselines.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Layers className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-medium text-[var(--text-primary)]">
              {t('browserAgent:regression.baseline')}s
            </h3>
            <span className="text-xs text-amber-400 px-1.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20">
              {baselines.length}
            </span>
          </div>
          <div className="space-y-2">
            {baselines.map((baseline) => (
              <div
                key={baseline.name}
                className="flex items-center justify-between p-3 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] hover:border-amber-500/25 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                    <Layers className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">{baseline.name}</p>
                    <div className="flex items-center gap-2 text-[11px] text-[var(--text-tertiary)]">
                      <span className="font-mono">{baseline.width}x{baseline.height}</span>
                      <span>·</span>
                      <span>{new Date(baseline.createdAt).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <div className="flex gap-1.5 shrink-0 ml-3">
                  <button
                    type="button"
                    onClick={() => handleCompare(baseline.name)}
                    disabled={isComparing}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-md border border-purple-500/30 text-purple-400 hover:bg-purple-500/10 disabled:opacity-50 transition-colors"
                  >
                    {isComparing ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <GitCompareArrows className="w-3 h-3" />
                    )}
                    {t('browserAgent:regression.compare')}
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteBaseline(projectPath, baseline.name)}
                    disabled={isLoading}
                    className="p-1.5 rounded-md border border-red-500/20 text-red-400/70 hover:text-red-400 hover:bg-red-500/10 disabled:opacity-50 transition-colors"
                    title={t('browserAgent:regression.deleteBaseline')}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Comparison results */}
      {comparisons.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <GitCompareArrows className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-medium text-[var(--text-primary)]">
              {t('browserAgent:regression.resultsTitle')}
            </h3>
          </div>
          <div className="space-y-3">
            {comparisons.map((comparison) => {
              const passed = comparison.passed;
              return (
                <div
                  key={comparison.name}
                  className={`p-4 rounded-lg border ${
                    passed
                      ? 'border-emerald-500/25 bg-emerald-500/5'
                      : 'border-rose-500/25 bg-rose-500/5'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {passed ? (
                        <CheckCircle2 className="w-4.5 h-4.5 text-emerald-400" />
                      ) : (
                        <XCircle className="w-4.5 h-4.5 text-rose-400" />
                      )}
                      <span className="text-sm font-medium text-[var(--text-primary)]">
                        {comparison.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${
                          passed
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/25'
                        }`}
                      >
                        {passed
                          ? t('browserAgent:regression.passed')
                          : t('browserAgent:regression.failed')}
                      </span>
                      <MatchPercentage value={comparison.matchPercentage} />
                    </div>
                  </div>
                  <div className="flex gap-4 text-xs text-[var(--text-tertiary)]">
                    <span>
                      {t('browserAgent:regression.diffPixels')}: <span className="text-orange-400 font-mono">{comparison.diffPixels.toLocaleString()}</span>
                    </span>
                    <span>
                      {t('browserAgent:regression.threshold')}: <span className="text-blue-400 font-mono">{comparison.threshold}%</span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

// ── MatchPercentage ─────────────────────────────────────────

function MatchPercentage({ value }: { readonly value: number }) {
  const color =
    value >= 95 ? 'text-emerald-400' : value >= 85 ? 'text-amber-400' : 'text-rose-400';
  const bgColor =
    value >= 95 ? 'bg-emerald-400' : value >= 85 ? 'bg-amber-400' : 'bg-rose-400';
  const trackColor =
    value >= 95 ? 'bg-emerald-500/15' : value >= 85 ? 'bg-amber-500/15' : 'bg-rose-500/15';

  return (
    <div className="flex items-center gap-2">
      <div className={`w-16 h-1.5 rounded-full ${trackColor} overflow-hidden`}>
        <div
          className={`h-full rounded-full ${bgColor} transition-all`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      <span className={`text-sm font-mono font-bold ${color}`}>
        {value}%
      </span>
    </div>
  );
}
