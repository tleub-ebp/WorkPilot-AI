import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  usePipelineGeneratorStore,
  generatePipelines,
  cancelPipelineGeneration,
  setupPipelineGeneratorListeners,
  CI_PLATFORMS,
  PLATFORM_LABELS,
  PLATFORM_ICONS,
  type CiPlatform,
} from '../../stores/pipeline-generator-store';
import { useProjectStore } from '../../stores/project-store';
import { ProjectSelector } from '../settings/ProjectSelector';

export function PipelineGenerator(): React.ReactElement {
  const { t } = useTranslation(['pipelineGenerator', 'common']);
  const activeProject = useProjectStore((s) => s.getActiveProject());
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const {
    phase,
    status,
    streamingOutput,
    result,
    error,
    selectedPlatforms,
    selectedPlatformView,
    togglePlatform,
    setSelectedPlatformView,
  } = usePipelineGeneratorStore();

  const isRunning = phase === 'generating';
  const isComplete = phase === 'complete';

  useEffect(() => {
    const cleanup = setupPipelineGeneratorListeners();
    return cleanup;
  }, []);

  function handleGenerate() {
    if (!activeProject?.path) return;
    generatePipelines(activeProject.path);
  }

  const selectedPipeline =
    result && selectedPlatformView ? result.pipelines[selectedPlatformView] : null;

  function handleCopyPipeline() {
    if (selectedPipeline) {
      navigator.clipboard.writeText(selectedPipeline).catch(console.error);
    }
  }

  return (
    <div className="flex flex-col h-full bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-color)]">
        <div>
          <h1 className="text-xl font-semibold">{t('pipelineGenerator:title')}</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-0.5">
            {t('pipelineGenerator:description')}
          </p>
        </div>
        <div className="flex gap-2">
          {isRunning ? (
            <button
              type="button"
              onClick={cancelPipelineGeneration}
              className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors text-sm font-medium"
            >
              {t('pipelineGenerator:actions.cancel')}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleGenerate}
              disabled={!activeProject || selectedPlatforms.length === 0}
              className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity text-sm font-medium"
            >
              {isComplete
                ? t('pipelineGenerator:actions.regenerate')
                : t('pipelineGenerator:actions.generate')}
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <div className="w-56 border-r border-[var(--border-color)] p-4 flex flex-col gap-4">
          {/* Project selection */}
          <div>
            <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
              {t('pipelineGenerator:project')}
            </h3>
            <ProjectSelector
              selectedProjectId={activeProjectId}
              onProjectChange={(id) => {
                if (id) setActiveProject(id);
              }}
            />
          </div>

          {/* Platform selection */}
          <div>
            <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
              {t('pipelineGenerator:platforms')}
            </h3>
            <div className="flex flex-col gap-1">
              {CI_PLATFORMS.map((platform) => (
                <label
                  key={platform}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[var(--bg-secondary)] cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedPlatforms.includes(platform)}
                    onChange={() => togglePlatform(platform)}
                    disabled={isRunning}
                    className="rounded accent-[var(--accent)]"
                  />
                  <span className="text-sm">
                    {PLATFORM_ICONS[platform]} {PLATFORM_LABELS[platform]}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Pipeline view selector (after generation) */}
          {isComplete && result && (
            <div>
              <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
                {t('pipelineGenerator:viewPipeline')}
              </h3>
              <div className="flex flex-col gap-1">
                {result.platforms_generated.map((platform) => (
                  <button
                    key={platform}
                    type="button"
                    onClick={() => setSelectedPlatformView(platform as CiPlatform)}
                    className={`flex items-center gap-2 px-2 py-1.5 rounded-md text-sm text-left transition-colors ${
                      selectedPlatformView === platform
                        ? 'bg-[var(--accent)]/20 text-[var(--accent)]'
                        : 'hover:bg-[var(--bg-secondary)]'
                    }`}
                  >
                    {PLATFORM_ICONS[platform as CiPlatform]}{' '}
                    {PLATFORM_LABELS[platform as CiPlatform]}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Detected stack info */}
          {isComplete && result?.stack && (
            <div className="mt-auto">
              <h3 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
                {t('pipelineGenerator:detectedStack')}
              </h3>
              <div className="flex flex-col gap-1 text-xs text-[var(--text-secondary)]">
                {result.stack.languages.length > 0 && (
                  <div>
                    <span className="opacity-70">{t('pipelineGenerator:stackInfo.languages')}: </span>
                    {result.stack.languages.join(', ')}
                  </div>
                )}
                {result.stack.frameworks.length > 0 && (
                  <div>
                    <span className="opacity-70">{t('pipelineGenerator:stackInfo.frameworks')}: </span>
                    {result.stack.frameworks.join(', ')}
                  </div>
                )}
                {result.stack.has_docker && (
                  <div className="text-blue-400">ðŸ³ {t('pipelineGenerator:stackInfo.dockerDetected')}</div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Main content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Status bar */}
          {(isRunning || status) && (
            <div className="px-4 py-2 bg-[var(--bg-secondary)] border-b border-[var(--border-color)] text-sm text-[var(--text-secondary)] flex items-center gap-2">
              {isRunning && (
// biome-ignore lint/a11y/noSvgWithoutTitle: SVG is decorative 
                <svg className="animate-spin w-4 h-4 text-[var(--accent)]" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
              )}
              {status}
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="m-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Pipeline YAML view */}
          {isComplete && selectedPipeline && (
            <div className="flex-1 overflow-auto p-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{PLATFORM_ICONS[selectedPlatformView as CiPlatform]}</span>
                  <h2 className="text-lg font-medium">
                    {PLATFORM_LABELS[selectedPlatformView as CiPlatform]}
                  </h2>
                  <span className="text-xs text-[var(--text-secondary)] ml-2 bg-[var(--bg-secondary)] px-2 py-0.5 rounded">
                    {selectedPipeline.split('\n').length} {t('pipelineGenerator:lines')}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleCopyPipeline}
                  className="px-3 py-1.5 text-xs rounded-md bg-[var(--bg-secondary)] hover:bg-[var(--border-color)] transition-colors"
                >
                  {t('pipelineGenerator:actions.copy')}
                </button>
              </div>
              <div className="bg-[var(--bg-secondary)] rounded-lg p-4 overflow-auto">
                <pre className="text-xs font-mono text-green-400 whitespace-pre overflow-x-auto">
                  {selectedPipeline}
                </pre>
              </div>
              {result?.saved_files?.[selectedPlatformView as CiPlatform] && (
                <p className="text-xs text-[var(--text-secondary)] mt-2">
                  {t('pipelineGenerator:savedTo')}{' '}
                  <code className="bg-[var(--bg-secondary)] px-1 rounded">
                    {result.saved_files[selectedPlatformView as CiPlatform]}
                  </code>
                </p>
              )}
            </div>
          )}

          {/* Streaming log */}
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
                <div className="text-5xl mb-4">âš™ï¸</div>
                <h3 className="text-lg font-medium mb-2">{t('pipelineGenerator:emptyState.title')}</h3>
                <p className="text-sm text-[var(--text-secondary)] max-w-sm">
                  {t('pipelineGenerator:emptyState.description')}
                </p>
                {!activeProject && (
                  <p className="text-sm text-amber-400 mt-3">
                    {t('pipelineGenerator:errors.noProject')}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PipelineGenerator;


