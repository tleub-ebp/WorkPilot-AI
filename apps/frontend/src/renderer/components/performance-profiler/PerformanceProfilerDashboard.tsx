import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  usePerformanceProfilerStore,
  startPerformanceProfiling,
  cancelPerformanceProfiling,
  type PerformanceProfilerPhase,
} from '../../stores/performance-profiler-store';
import { useProjectStore } from '../../stores/project-store';

const PHASE_LABELS: Record<PerformanceProfilerPhase, string> = {
  idle: 'Ready',
  profiling: 'Profiling codebase...',
  analyzing: 'Running benchmarks...',
  optimizing: 'Generating optimizations...',
  complete: 'Complete',
  error: 'Error',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/10 border-red-500/20',
  high: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  low: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
};

const EFFORT_LABELS: Record<string, string> = {
  trivial: 'Trivial',
  low: 'Low effort',
  medium: 'Medium effort',
  high: 'High effort',
};

export function PerformanceProfilerDashboard(): React.ReactElement {
  const { t } = useTranslation(['common']);
  const activeProject = useProjectStore((s) => s.getActiveProject());
  const {
    phase,
    status,
    streamingOutput,
    result,
    implementationResult,
    error,
    autoImplement,
    setAutoImplement,
  } = usePerformanceProfilerStore();

  const isRunning = ['profiling', 'analyzing', 'optimizing'].includes(phase);
  const isComplete = phase === 'complete';

  function handleStart() {
    if (!activeProject?.path) return;
    startPerformanceProfiling(activeProject.path);
  }

  const criticalCount = result?.report?.bottlenecks.filter((b) => b.severity === 'critical').length ?? 0;
  const highCount = result?.report?.bottlenecks.filter((b) => b.severity === 'high').length ?? 0;

  return (
    <div className="flex flex-col h-full bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[var(--border-color)]">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Performance Profiler</h1>
            <p className="text-sm text-[var(--text-secondary)] mt-0.5">
              Identify bottlenecks and auto-generate optimizations
            </p>
          </div>
          <div className="flex items-center gap-3">
            {isRunning ? (
              <button
                onClick={cancelPerformanceProfiling}
                className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors text-sm font-medium"
              >
                Cancel
              </button>
            ) : (
              <button
                onClick={handleStart}
                disabled={!activeProject}
                className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity text-sm font-medium"
              >
                {isComplete ? 'Re-analyze' : 'Analyze Performance'}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <div className="w-56 border-r border-[var(--border-color)] p-4 flex flex-col gap-4">
          {/* Options */}
          <div>
            <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-3">
              Options
            </h3>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoImplement}
                onChange={(e) => setAutoImplement(e.target.checked)}
                disabled={isRunning}
                className="rounded accent-[var(--accent)]"
              />
              <div>
                <div className="text-sm font-medium">Auto-implement</div>
                <div className="text-xs text-[var(--text-secondary)]">Apply safe fixes automatically</div>
              </div>
            </label>
          </div>

          {/* Summary stats */}
          {isComplete && result?.report?.summary && (
            <div>
              <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
                Summary
              </h3>
              <div className="flex flex-col gap-2">
                <div className="bg-[var(--bg-secondary)] rounded-lg p-2.5">
                  <div className="text-lg font-bold">{result.report.summary.total_bottlenecks}</div>
                  <div className="text-xs text-[var(--text-secondary)]">Bottlenecks found</div>
                </div>
                {criticalCount > 0 && (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2.5">
                    <div className="text-lg font-bold text-red-400">{criticalCount}</div>
                    <div className="text-xs text-red-400/70">Critical</div>
                  </div>
                )}
                {highCount > 0 && (
                  <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-2.5">
                    <div className="text-lg font-bold text-orange-400">{highCount}</div>
                    <div className="text-xs text-orange-400/70">High priority</div>
                  </div>
                )}
                <div className="bg-[var(--bg-secondary)] rounded-lg p-2.5">
                  <div className="text-lg font-bold">{result.report.summary.total_suggestions}</div>
                  <div className="text-xs text-[var(--text-secondary)]">Optimizations</div>
                </div>
              </div>
            </div>
          )}

          {/* Phase indicator */}
          {phase !== 'idle' && (
            <div className="mt-auto">
              <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                {isRunning && (
                  <svg className="animate-spin w-3.5 h-3.5 text-[var(--accent)] shrink-0" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                <span className="text-xs">{PHASE_LABELS[phase]}</span>
              </div>
              {status && status !== PHASE_LABELS[phase] && (
                <div className="text-xs text-[var(--text-secondary)] mt-1 ml-5">{status}</div>
              )}
            </div>
          )}
        </div>

        {/* Main content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Error */}
          {error && (
            <div className="m-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Results */}
          {isComplete && result && (
            <div className="flex-1 overflow-auto p-4 flex flex-col gap-4">
              {/* Implementation result banner */}
              {implementationResult && (
                <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
                  ✅ Auto-implementation complete
                </div>
              )}

              {/* Benchmarks */}
              {(result.report?.benchmarks?.length ?? 0) > 0 && (
                <div>
                  <h2 className="text-sm font-semibold mb-2">Benchmarks</h2>
                  <div className="grid grid-cols-2 gap-2">
                    {result.report.benchmarks.map((b, i) => (
                      <div key={i} className="bg-[var(--bg-secondary)] rounded-lg p-3">
                        <div className="text-xs text-[var(--text-secondary)] mb-1">{b.name}</div>
                        <div className="text-sm font-mono">
                          {b.duration_ms != null ? `${b.duration_ms.toFixed(1)}ms` : 'N/A'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Bottlenecks */}
              {(result.report?.bottlenecks?.length ?? 0) > 0 ? (
                <div>
                  <h2 className="text-sm font-semibold mb-2">
                    Bottlenecks ({result.report.bottlenecks.length})
                  </h2>
                  <div className="flex flex-col gap-2">
                    {result.report.bottlenecks.map((b, i) => (
                      <div
                        key={i}
                        className={`rounded-lg p-3 border ${SEVERITY_COLORS[b.severity] ?? 'border-[var(--border-color)]'}`}
                      >
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <div className="font-medium text-sm">{b.description}</div>
                          <span className={`text-xs px-1.5 py-0.5 rounded font-medium shrink-0 ${SEVERITY_COLORS[b.severity] ?? ''}`}>
                            {b.severity}
                          </span>
                        </div>
                        {b.file_path && (
                          <div className="text-xs opacity-70 font-mono mb-1">
                            {b.file_path}{b.line_start ? `:${b.line_start}` : ''}
                          </div>
                        )}
                        <div className="text-xs opacity-80">{b.type.replace(/_/g, ' ')}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-[var(--text-secondary)] text-center py-8">
                  No bottlenecks detected 🎉
                </div>
              )}

              {/* Suggestions */}
              {(result.report?.suggestions?.length ?? 0) > 0 && (
                <div>
                  <h2 className="text-sm font-semibold mb-2">
                    Optimizations ({result.report.suggestions.length})
                  </h2>
                  <div className="flex flex-col gap-3">
                    {result.report.suggestions.map((s, i) => (
                      <div key={i} className="bg-[var(--bg-secondary)] rounded-lg p-3">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <div className="font-medium text-sm">{s.title}</div>
                          <span className="text-xs text-[var(--text-secondary)] shrink-0">
                            {EFFORT_LABELS[s.effort] ?? s.effort}
                          </span>
                        </div>
                        <div className="text-xs text-[var(--text-secondary)] mb-2">{s.description}</div>
                        {s.estimated_improvement && (
                          <div className="text-xs text-green-400">
                            ↑ {s.estimated_improvement}
                          </div>
                        )}
                        {s.implementation && (
                          <details className="mt-2">
                            <summary className="text-xs text-[var(--accent)] cursor-pointer">
                              View implementation
                            </summary>
                            <pre className="mt-1 text-xs font-mono text-[var(--text-secondary)] whitespace-pre-wrap overflow-x-auto bg-[var(--bg-primary)] rounded p-2">
                              {s.implementation}
                            </pre>
                          </details>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Streaming output */}
          {(isRunning || (!isComplete && streamingOutput)) && (
            <div className="flex-1 overflow-auto p-4">
              <pre className="text-xs font-mono text-[var(--text-secondary)] whitespace-pre-wrap">
                {streamingOutput}
              </pre>
            </div>
          )}

          {/* Empty state */}
          {phase === 'idle' && !result && (
            <div className="flex-1 flex items-center justify-center text-center p-8">
              <div>
                <div className="text-5xl mb-4">⚡</div>
                <h3 className="text-lg font-medium mb-2">Performance Profiler</h3>
                <p className="text-sm text-[var(--text-secondary)] max-w-sm">
                  Analyze your codebase for performance bottlenecks — algorithm complexity,
                  memory leaks, slow queries, React render issues, and more.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PerformanceProfilerDashboard;
