/**
 * TaskLockBadge — Shows a lock indicator on tasks in the Kanban board.
 *
 * Displays 🔒 for user locks and 🤖 for agent locks.
 * Clicking on the badge shows lock details and allows force-unlock for admins.
 *
 * Feature 3.1 — Mode multi-utilisateurs en temps réel.
 */

import { Lock, Bot, Unlock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '../../lib/utils';
import { useCollaborationStore, } from '../../stores/collaboration-store';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../ui/popover';
import { Button } from '../ui/button';

interface TaskLockBadgeProps {
  taskId: string;
  className?: string;
  showForceUnlock?: boolean;
}

export function TaskLockBadge({ taskId, className, showForceUnlock = false }: TaskLockBadgeProps) {
  const { t } = useTranslation('collaboration');
  const lock = useCollaborationStore((s) => s.getTaskLock(taskId));
  const unlockTask = useCollaborationStore((s) => s.unlockTask);
  const currentUserId = useCollaborationStore((s) => s.currentUserId);
  const users = useCollaborationStore((s) => s.users);

  if (!lock) return null;

  const isAgentLock = lock.lockType === 'agent';
  const isOwnLock = lock.lockedBy === currentUserId;
  const lockerName = users.find((u) => u.userId === lock.lockedBy)?.displayName ?? lock.lockedBy;

  const label = isAgentLock
    ? t('locks.lockedByAgent', { agent: lock.lockedBy.replace('agent:', '') })
    : t('locks.lockedBy', { user: lockerName });

  const Icon = isAgentLock ? Bot : Lock;

  if (showForceUnlock && !isOwnLock) {
    return (
      <Popover>
        <PopoverTrigger asChild>
          <button
            className={cn(
              'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium',
              isAgentLock
                ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                : 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
              className
            )}
          >
            <Icon className="h-3 w-3" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-3" side="top">
          <div className="space-y-2">
            <p className="text-sm font-medium">{label}</p>
            {lock.reason && (
              <p className="text-xs text-muted-foreground">
                {t('locks.lockReason')}: {lock.reason}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              {isAgentLock
                ? t('locks.agentLockedWarning')
                : t('locks.taskLockedWarning', { user: lockerName })}
            </p>
            <Button
              size="sm"
              variant="destructive"
              className="w-full gap-1.5"
              onClick={() => unlockTask(taskId)}
            >
              <Unlock className="h-3 w-3" />
              {t('locks.forceUnlock')}
            </Button>
          </div>
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium',
              isAgentLock
                ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                : 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
              className
            )}
          >
            <Icon className="h-3 w-3" />
          </span>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p>{label}</p>
          {lock.reason && <p className="text-xs text-muted-foreground">{lock.reason}</p>}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
