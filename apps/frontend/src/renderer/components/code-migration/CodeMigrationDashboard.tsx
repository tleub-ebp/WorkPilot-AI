import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  useCodeMigrationStore,
  startCodeMigration,
  cancelCodeMigration,
  type CodeMigrationPhase,
} from '../../stores/code-migration-store';
import { useProjectStore } from '../../stores/project-store';

const PHASE_LABELS: Record<CodeMigrationPhase, string> = {
  idle: 'Ready',
  analyzing: 'Analyzing codebase...',
  planning: 'Planning migration...',
  executing: 'Executing migration...',
  validating: 'Validating changes...',
  complete: 'Complete',
  error: 'Error',
};

const EXAMPLE_MIGRATIONS = [
  'Migrate React Class Components to Hooks',
  'Convert JavaScript files to TypeScript',
  'Upgrade Python 3.9 deprecated patterns to 3.12',
  'Replace callbacks with async/await',
  'Migrate from Moment.js to date-fns',
];

export function CodeMigrationDashboard(): React.ReactElement {
  // biome-ignore lint/correctness/noUnusedVariables: variable kept for clarity
  const { t } = useTranslation(['common']);
  const activeProject = useProjectStore((s) => s.getActiveProject());
  const {
    phase,
    status,
    streamingOutput,
    result,
    error,
    migrationDescription,
    dryRun,
    taskProgress,
    setMigrationDescription,
    setDryRun,
  } = useCodeMigrationStore();

  const isRunning = ['analyzing', 'planning', 'executing', 'validating'].includes(phase);
  const isComplete = phase === 'complete';

  function handleStart() {
    if (!activeProject?.path || !migrationDescription.trim()) return;
    startCodeMigration(activeProject.path);
  }

  function handleExample(example: string) {
    setMigrationDescription(example);
  }

  return (
    <div className="flex flex-col h-full bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[var(--border-color)]">
        <h1 className="text-xl font-semibold">Code Migration Agent</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-0.5">
          Automated framework, version, and language migrations
        </p>
      </div>

      <div className="flex flex-1 overflow-hidden gap-0">
        {/* Left: Config panel */}
        <div className="w-72 border-r border-[var(--border-color)] p-4 flex flex-col gap-4 overflow-y-auto">
          <div>
            // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
            <label className="block text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
              Migration Description
            </label>
            <textarea
              value={migrationDescription}
              onChange={(e) => setMigrationDescription(e.target.value)}
              disabled={isRunning}
              placeholder="Describe the migration you want to perform..."
              rows={4}
              className="w-full rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-[var(--accent)] disabled:opacity-50"
            />
          </div>

          {/* Example migrations */}
          <div>
            <p className="text-xs text-[var(--text-secondary)] mb-2">Examples:</p>
            <div className="flex flex-col gap-1">
              {EXAMPLE_MIGRATIONS.map((ex) => (
                <button type="button"
                  key={ex}
                  onClick={() => handleExample(ex)}
                  disabled={isRunning}
                  className="text-left text-xs px-2 py-1.5 rounded-md bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors disabled:opacity-50"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>

          {/* Options */}
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                disabled={isRunning}
                className="rounded accent-[var(--accent)]"
              />
              <div>
                <div className="text-sm font-medium">Dry Run</div>
                <div className="text-xs text-[var(--text-secondary)]">Analyze only, no file changes</div>
              </div>
            </label>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2 mt-auto">
            {isRunning ? (
              <button type="button"
                onClick={cancelCodeMigration}
                className="w-full px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors text-sm font-medium"
              >
                Cancel Migration
              </button>
            ) : (
              <button type="button"
                onClick={handleStart}
                disabled={!activeProject || !migrationDescription.trim()}
                className="w-full px-4 py-2 rounded-lg bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity text-sm font-medium"
              >
                {dryRun ? 'Analyze Migration' : 'Start Migration'}
              </button>
            )}
          </div>
        </div>

        {/* Right: Output panel */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Phase indicator */}
          {phase !== 'idle' && (
            <div className="px-4 py-2 bg-[var(--bg-secondary)] border-b border-[var(--border-color)] flex items-center gap-3">
              {isRunning && (
// biome-ignore lint/a11y/noSvgWithoutTitle: SVG is decorative 
                <svg className="animate-spin w-4 h-4 text-[var(--accent)] shrink-0" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
              <span className="text-sm text-[var(--text-secondary)]">{PHASE_LABELS[phase]}</span>
              {status && status !== PHASE_LABELS[phase] && (
                <span className="text-sm text-[var(--text-secondary)] ml-1">â€” {status}</span>
              )}
              {/* Task progress */}
              {taskProgress && taskProgress.total > 0 && (
                <div className="ml-auto flex items-center gap-2">
                  <div className="w-32 h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--accent)] transition-all duration-300"
                      style={{ width: `${(taskProgress.current / taskProgress.total) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-[var(--text-secondary)]">
                    {taskProgress.current}/{taskProgress.total}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="m-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Results */}
          {isComplete && result && (
            <div className="p-4 border-b border-[var(--border-color)]">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl">{result.dry_run ? 'ðŸ”' : 'âœ…'}</span>
                <div>
                  <h3 className="font-medium">
                    {result.dry_run ? 'Dry Run Analysis Complete' : 'Migration Complete'}
                  </h3>
                  <p className="text-sm text-[var(--text-secondary)]">{result.migration_description}</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-[var(--bg-secondary)] rounded-lg p-3 text-center">
                  <div className="text-xl font-bold">{result.summary.files_modified}</div>
                  <div className="text-xs text-[var(--text-secondary)]">Files Modified</div>
                </div>
                <div className="bg-[var(--bg-secondary)] rounded-lg p-3 text-center">
                  <div className="text-xl font-bold capitalize">{result.summary.plan_status}</div>
                  <div className="text-xs text-[var(--text-secondary)]">Plan Status</div>
                </div>
                <div className="bg-[var(--bg-secondary)] rounded-lg p-3 text-center">
                  <div className="text-xl font-bold capitalize">{result.summary.execution_status}</div>
                  <div className="text-xs text-[var(--text-secondary)]">Execution</div>
                </div>
              </div>
            </div>
          )}

          {/* Streaming output */}
          <div className="flex-1 overflow-auto p-4">
            {streamingOutput ? (
              <pre className="text-xs font-mono text-[var(--text-secondary)] whitespace-pre-wrap">
                {streamingOutput}
              </pre>
            ) : phase === 'idle' ? (
              <div className="flex items-center justify-center h-full text-center">
                <div>
                  <div className="text-5xl mb-4">ðŸ”„</div>
                  <h3 className="text-lg font-medium mb-2">Code Migration Agent</h3>
                  <p className="text-sm text-[var(--text-secondary)] max-w-sm">
                    Describe the migration you want to perform and click Start.
                    Use Dry Run first to preview changes before applying them.
                  </p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default CodeMigrationDashboard;



