import { useTranslation } from 'react-i18next';
import type { RepoExecutionState, MultiRepoStatus } from '@shared/types';

interface ExecutionMonitorProps {
  status: MultiRepoStatus;
  repoStates: RepoExecutionState[];
  overallProgress: number;
  currentRepo: string | null;
  statusMessage: string;
}

const STATUS_ICONS: Record<string, string> = {
  pending: '○',
  analyzing: '◌',
  planning: '◎',
  coding: '●',
  qa: '◉',
  completed: '✓',
  failed: '✗',
  skipped: '—',
};

/**
 * ExecutionMonitor - Shows per-repo execution progress
 */
export function ExecutionMonitor({
  status,
  repoStates,
  overallProgress,
  currentRepo,
  statusMessage,
}: ExecutionMonitorProps) {
  const { t } = useTranslation(['multiRepo']);

  return (
    <div className="space-y-4">
      {/* Overall progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-foreground">
            {t(`multiRepo:status.${status}`)}
          </span>
          <span className="text-muted-foreground">
            {Math.round(overallProgress)}%
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-muted">
          <div
            className="h-2 rounded-full bg-primary transition-all duration-500"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
        {statusMessage && (
          <p className="text-xs text-muted-foreground">{statusMessage}</p>
        )}
      </div>

      {/* Per-repo status */}
      {repoStates.length > 0 && (
        <div className="space-y-2">
          {repoStates.map((rs) => {
            const isCurrent = rs.repo === currentRepo;
            const displayName = rs.repo.split('/').pop() || rs.repo;
            const icon = STATUS_ICONS[rs.status] || '○';
            const isComplete = rs.status === 'completed';
            const isFailed = rs.status === 'failed';

            return (
              <div
                key={rs.repo}
                className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
                  isCurrent
                    ? 'border-primary bg-primary/5'
                    : isComplete
                      ? 'border-green-500/30 bg-green-500/5'
                      : isFailed
                        ? 'border-destructive/30 bg-destructive/5'
                        : 'border-border bg-card'
                }`}
              >
                {/* Status icon */}
                <span
                  className={`text-base ${
                    isComplete
                      ? 'text-green-500'
                      : isFailed
                        ? 'text-destructive'
                        : isCurrent
                          ? 'text-primary'
                          : 'text-muted-foreground'
                  }`}
                >
                  {icon}
                </span>

                {/* Repo info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground truncate">
                      {displayName}
                    </span>
                    {rs.currentPhase && (
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                        {rs.currentPhase}
                      </span>
                    )}
                  </div>
                  {rs.errorMessage && (
                    <p className="text-xs text-destructive mt-0.5 truncate">
                      {rs.errorMessage}
                    </p>
                  )}
                  {rs.prUrl && (
                    <p className="text-xs text-primary mt-0.5 truncate">
                      PR: {rs.prUrl}
                    </p>
                  )}
                </div>

                {/* Progress */}
                <div className="flex items-center gap-2">
                  {rs.progress > 0 && rs.progress < 100 && (
                    <div className="h-1.5 w-16 rounded-full bg-muted">
                      <div
                        className="h-1.5 rounded-full bg-primary transition-all duration-500"
                        style={{ width: `${rs.progress}%` }}
                      />
                    </div>
                  )}
                  <span className="text-xs text-muted-foreground w-8 text-right">
                    {Math.round(rs.progress)}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
