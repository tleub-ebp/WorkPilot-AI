import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useMultiRepoStore } from '@/stores/multi-repo-store';
import { RepoSelector } from './RepoSelector';
import { DependencyGraphView } from './DependencyGraphView';
import { ExecutionMonitor } from './ExecutionMonitor';
import { BreakingChangeBanner } from './BreakingChangeBanner';
import type { MultiRepoCreateConfig } from '@shared/types';

/**
 * MultiRepoDialog - Main dialog for creating and monitoring multi-repo orchestrations
 *
 * Steps:
 * 1. Add repositories (RepoSelector)
 * 2. Describe the cross-repo task
 * 3. Review dependency graph
 * 4. Monitor execution progress
 */
export function MultiRepoDialog() {
  const { t } = useTranslation(['multiRepo', 'common']);
  const {
    isDialogOpen,
    closeDialog,
    targetRepos,
    taskDescription,
    setTaskDescription,
    status,
    repoStates,
    dependencyGraph,
    executionOrder,
    breakingChanges,
    overallProgress,
    currentRepo,
    statusMessage,
    isCreating,
    setIsCreating,
    activeOrchestration,
  } = useMultiRepoStore();

  const isExecuting = status !== 'pending' && status !== 'completed' && status !== 'failed';
  const isConfiguring = status === 'pending' && !activeOrchestration;

  const handleCreate = useCallback(async () => {
    if (targetRepos.length < 2 || !taskDescription.trim()) return;

    setIsCreating(true);
    try {
      const config: MultiRepoCreateConfig = {
        repos: targetRepos.map((r) => ({
          repo: r.repo,
          localPath: r.localPath,
          pathScope: r.pathScope,
        })),
        taskDescription: taskDescription.trim(),
      };

      // The actual IPC call would be made by a hook or effect
      // For now we just store the config
      const result = await window.electronAPI.createMultiRepoOrchestration(
        '', // projectId - will be resolved by the handler
        config
      );

      if (result?.success && result.data) {
        useMultiRepoStore.getState().setActiveOrchestration(result.data);
      }
    } catch (error) {
      console.error('[MultiRepo] Create failed:', error);
    } finally {
      setIsCreating(false);
    }
  }, [targetRepos, taskDescription, setIsCreating]);

  const handleStart = useCallback(async () => {
    if (!activeOrchestration) return;
    try {
      await window.electronAPI.startMultiRepoOrchestration(
        '', // projectId
        activeOrchestration.id
      );
    } catch (error) {
      console.error('[MultiRepo] Start failed:', error);
    }
  }, [activeOrchestration]);

  if (!isDialogOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
{/* biome-ignore lint/a11y/noStaticElementInteractions: intentional */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={closeDialog}
        onKeyDown={(e) => e.key === 'Escape' && closeDialog()}
        role="presentation"
      />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-2xl max-h-[85vh] overflow-auto rounded-xl border border-border bg-background shadow-xl">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {t('multiRepo:dialog.title')}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t('multiRepo:dialog.description')}
            </p>
          </div>
          <button
            type="button"
            onClick={closeDialog}
            className="rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            {/* biome-ignore lint/a11y/noSvgWithoutTitle: SVG is decorative, intentional  */}
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Step 1: Repos */}
          {isConfiguring && (
            <>
              <section>
                <h3 className="mb-3 text-sm font-medium text-foreground">
                  {t('multiRepo:dialog.stepRepos')}
                </h3>
                <RepoSelector />
              </section>

              {/* Step 2: Task description */}
              <section>
                <h3 className="mb-2 text-sm font-medium text-foreground">
                  {t('multiRepo:dialog.stepTask')}
                </h3>
                <textarea
                  value={taskDescription}
                  onChange={(e) => setTaskDescription(e.target.value)}
                  placeholder={t('multiRepo:dialog.taskPlaceholder')}
                  rows={4}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              </section>
            </>
          )}

          {/* Step 3: Dependency graph (shown after creation or during execution) */}
          {dependencyGraph && dependencyGraph.nodes.length > 0 && (
            <DependencyGraphView
              graph={dependencyGraph}
              executionOrder={executionOrder}
              repoStates={repoStates}
            />
          )}

          {/* Breaking changes */}
          <BreakingChangeBanner breakingChanges={breakingChanges} />

          {/* Step 4: Execution monitor (shown during execution) */}
          {(isExecuting || status === 'completed' || status === 'failed') && (
            <ExecutionMonitor
              status={status}
              repoStates={repoStates}
              overallProgress={overallProgress}
              currentRepo={currentRepo}
              statusMessage={statusMessage}
            />
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 flex items-center justify-end gap-3 border-t border-border bg-background px-6 py-4">
          <button
            type="button"
            onClick={closeDialog}
            className="rounded-md border border-border px-4 py-2 text-sm text-foreground hover:bg-accent transition-colors"
          >
            {t('common:cancel')}
          </button>

          {isConfiguring && (
            <button
              type="button"
              onClick={handleCreate}
              disabled={targetRepos.length < 2 || !taskDescription.trim() || isCreating}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isCreating
                ? t('multiRepo:dialog.creating')
                : t('multiRepo:dialog.createOrchestration')}
            </button>
          )}

          {activeOrchestration && status === 'pending' && (
            <button
              type="button"
              onClick={handleStart}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              {t('multiRepo:dialog.startOrchestration')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}



