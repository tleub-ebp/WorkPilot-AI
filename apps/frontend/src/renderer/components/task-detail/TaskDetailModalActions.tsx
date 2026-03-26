import { Play, Square, RotateCcw, Loader2, CheckCircle2, GitPullRequest } from 'lucide-react';
import { Button } from '../ui/button';
import { useTranslation } from 'react-i18next';
import { TASK_STATUS_LABELS } from '../../../shared/constants';
import { StreamingSessionButton } from '../streaming/StreamingSessionButton';
import type { Task, Project } from '../../../shared/types';

interface TaskDetailModalActionsProps {
  readonly task: Task;
  readonly activeProject?: Project;
  readonly state: ReturnType<typeof import('./hooks/useTaskDetail').useTaskDetail>;
  readonly handleStartStop: () => Promise<void>;
  readonly handleRecover: () => Promise<void>;
}

export function TaskDetailModalActions({ 
  task, 
  activeProject, 
  state, 
  handleStartStop, 
  handleRecover 
}: TaskDetailModalActionsProps) {
  const { t } = useTranslation(['tasks']);

  // Render primary action button based on state
  if (state.isStuck) {
    return (
      <Button
        variant="warning"
        onClick={handleRecover}
        disabled={state.isRecovering}
      >
        {state.isRecovering ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Recovering...
          </>
        ) : (
          <>
            <RotateCcw className="mr-2 h-4 w-4" />
            Recover Task
          </>
        )}
      </Button>
    );
  }

  if (state.isIncomplete) {
    return (
      <Button variant="default" onClick={handleStartStop} disabled={state.isLoadingPlan}>
        {state.isLoadingPlan ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading Plan...
          </>
        ) : (
          <>
            <Play className="mr-2 h-4 w-4" />
            Resume Task
          </>
        )}
      </Button>
    );
  }

  if (task.status === 'backlog' || task.status === 'queue' || task.status === 'in_progress') {
    return (
      <div className="flex items-center gap-2">
        {/* Watch Live button - show when project path is available */}
        {activeProject?.path && (
          <StreamingSessionButton
            taskId={task.id}
            projectPath={activeProject.path}
          />
        )}
        
        <Button
          variant={state.isRunning ? 'destructive' : 'default'}
          onClick={handleStartStop}
        >
          {state.isRunning ? (
            <>
              <Square className="mr-2 h-4 w-4" />
              {t('tasks:modal.actions.stopTask')}
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4" />
              {t('tasks:modal.actions.startTask')}
            </>
          )}
        </Button>
      </div>
    );
  }

  if (task.status === 'done' && task.metadata?.prUrl) {
    return (
      <div className="flex items-center gap-4">
        <div className="completion-state text-sm flex items-center gap-2 text-success">
          <CheckCircle2 className="h-5 w-5" />
          <span className="font-medium">{t('tasks:status.complete')}</span>
        </div>
         {task.metadata?.prUrl && (
           <button
             type="button"
             onClick={() => {
               if (task.metadata?.prUrl) {
                 globalThis.window.electronAPI?.openExternal(task.metadata.prUrl);
               }
             }}
             className="completion-state text-sm flex items-center gap-2 text-info cursor-pointer hover:underline bg-transparent border-none p-0"
           >
            <GitPullRequest className="h-5 w-5" />
            <span className="font-medium">{t(TASK_STATUS_LABELS[task.status])}</span>
          </button>
        )}
      </div>
    );
  }

  if (task.status === 'done') {
    return (
      <div className="completion-state text-sm flex items-center gap-2 text-success">
        <CheckCircle2 className="h-5 w-5" />
        <span className="font-medium">{t('tasks:status.complete')}</span>
      </div>
    );
  }

  return null;
}
