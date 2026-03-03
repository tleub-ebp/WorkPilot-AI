import { FileText, GitCommit, Loader2, ArrowRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { TaskCard, CommitCard } from './ChangelogEntry';
import type { ChangelogTask, ChangelogSourceMode, GitCommit as GitCommitType } from '../../../shared/types';

interface ChangelogListProps {
  readonly sourceMode: ChangelogSourceMode;
  // Task mode
  readonly doneTasks: ChangelogTask[];
  readonly selectedTaskIds: string[];
  readonly onToggleTask: (taskId: string) => void;
  readonly onSelectAll: () => void;
  readonly onDeselectAll: () => void;
  // Git mode
  readonly previewCommits: GitCommitType[];
  readonly isLoadingCommits: boolean;
  // Continue
  readonly onContinue: () => void;
  readonly canContinue: boolean;
}

export function ChangelogList({
  sourceMode,
  doneTasks,
  selectedTaskIds,
  onToggleTask,
  onSelectAll,
  onDeselectAll,
  previewCommits,
  isLoadingCommits,
  onContinue,
  canContinue
}: ChangelogListProps) {
  const { t } = useTranslation(['changelog', 'errors', 'common']);


  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Tasks Mode - Task Selection */}
      {sourceMode === 'tasks' && (
        <>
          {/* Task selection header */}
          <div className="flex items-center justify-between border-b border-border px-6 py-3 bg-muted/30">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium">
                {t('changelog:configuration.tasksSelectedCount', { selected: selectedTaskIds.length, total: doneTasks.length })}
              </span>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onSelectAll}
                  className="h-7 px-2 text-xs"
                >
                  {t('changelog:actions.selectAll')}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onDeselectAll}
                  className="h-7 px-2 text-xs"
                >
                  {t('changelog:actions.clear')}
                </Button>
              </div>
            </div>
          </div>

          {/* Task grid */}
          <ScrollArea className="flex-1 p-6">
            {doneTasks.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-center py-12">
                  <FileText className="mx-auto h-12 w-12 text-muted-foreground/30" />
                  <h3 className="mt-4 text-lg font-medium">{t('errors:noTasks')}</h3>
                  <p className="mt-2 text-sm text-muted-foreground max-w-md">
                    {t('errors:noTasksDescription')}
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {doneTasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    isSelected={selectedTaskIds.includes(task.id)}
                    onToggle={() => onToggleTask(task.id)}
                  />
                ))}
              </div>
            )}
          </ScrollArea>
        </>
      )}

      {/* Git History / Branch Diff Mode - Commit Preview */}
      {(sourceMode === 'git-history' || sourceMode === 'branch-diff') && (
        <>
          {/* Commit preview header */}
          <div className="flex items-center justify-between border-b border-border px-6 py-3 bg-muted/30">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium">
                {t('changelog:gitHistory.commitsFound', { count: previewCommits.length })}
              </span>
              {isLoadingCommits && (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              )}
            </div>
          </div>

          {/* Commit list */}
          <ScrollArea className="flex-1 p-6">
            {(() => {
              if (isLoadingCommits) {
                return (
                  <div className="flex h-full items-center justify-center">
                    <div className="text-center py-12">
                      <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
                      <p className="mt-4 text-sm text-muted-foreground">{t('changelog:gitHistory.loadingCommits')}</p>
                    </div>
                  </div>
                );
              }

              if (previewCommits.length === 0) {
                const noCommitsMessage = sourceMode === 'git-history'
                  ? t('errors:noCommitsGitHistory')
                  : t('errors:noCommitsBranchDiff');

                return (
                  <div className="flex h-full items-center justify-center">
                    <div className="text-center py-12">
                      <GitCommit className="mx-auto h-12 w-12 text-muted-foreground/30" />
                      <h3 className="mt-4 text-lg font-medium">{t('changelog:gitHistory.noCommits')}</h3>
                      <p className="mt-2 text-sm text-muted-foreground max-w-md">
                        {noCommitsMessage}
                      </p>
                    </div>
                  </div>
                );
              }

              return (
                <div className="space-y-2">
                  {previewCommits.map((commit) => (
                    <CommitCard key={commit.fullHash} commit={commit} />
                  ))}
                </div>
              );
            })()}
          </ScrollArea>
        </>
      )}

      {/* Footer with the Continue button */}
      <div className="flex items-center justify-end border-t border-border px-6 py-4 bg-background">
        <Button onClick={onContinue} disabled={!canContinue} size="lg">
          {t('common:actions.next')}
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
