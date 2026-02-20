/**
 * CollaborationNotifications — Real-time toast notifications for collaboration events.
 *
 * Listens to the collaboration store events and displays toasts for:
 * - User join/leave
 * - Task lock/unlock
 * - Agent started/completed
 * - Conflict detected
 * - Chat mentions
 *
 * Feature 3.1 — Mode multi-utilisateurs en temps réel.
 */

import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useCollaborationStore, type RealtimeEvent } from '../../stores/collaboration-store';
import { toast } from '../../hooks/use-toast';

export function CollaborationNotifications() {
  const { t } = useTranslation('collaboration');
  const events = useCollaborationStore((s) => s.events);
  const settings = useCollaborationStore((s) => s.settings);
  const currentUserId = useCollaborationStore((s) => s.currentUserId);
  const lastProcessed = useRef(0);

  useEffect(() => {
    if (events.length <= lastProcessed.current) return;

    const newEvents = events.slice(lastProcessed.current);
    lastProcessed.current = events.length;

    for (const event of newEvents) {
      if (event.senderId === currentUserId) continue;

      const notification = getNotification(event, t, settings);
      if (notification) {
        toast({
          title: notification.title,
          description: notification.description,
          variant: notification.variant as 'default' | 'destructive' | undefined,
        });
      }
    }
  }, [events, currentUserId, settings, t]);

  return null;
}

interface NotificationInfo {
  title: string;
  description: string;
  variant: string;
}

function getNotification(
  event: RealtimeEvent,
  t: (key: string, opts?: Record<string, unknown>) => string,
  settings: { notifyUserJoinLeave: boolean; notifyTaskLocks: boolean; notifyAgentActivity: boolean; notifyConflicts: boolean; notifyChatMentions: boolean }
): NotificationInfo | null {
  const data = event.data as Record<string, string>;

  switch (event.eventType) {
    case 'user_joined':
      if (!settings.notifyUserJoinLeave) return null;
      return {
        title: '👤 ' + t('notifications.userJoined', { user: data.display_name || data.user_id }),
        description: '',
        variant: 'default',
      };

    case 'user_left':
      if (!settings.notifyUserJoinLeave) return null;
      return {
        title: '👤 ' + t('notifications.userLeft', { user: data.display_name || data.user_id }),
        description: '',
        variant: 'default',
      };

    case 'task_locked':
      if (!settings.notifyTaskLocks) return null;
      return {
        title: '🔒 ' + t('notifications.taskLocked', { user: data.locked_by, task: data.task_id }),
        description: data.reason || '',
        variant: 'default',
      };

    case 'task_unlocked':
      if (!settings.notifyTaskLocks) return null;
      return {
        title: '🔓 ' + t('notifications.taskUnlocked', { user: data.unlocked_by, task: data.task_id }),
        description: '',
        variant: 'default',
      };

    case 'agent_started':
      if (!settings.notifyAgentActivity) return null;
      return {
        title: '🤖 ' + t('notifications.agentStarted', { agent: data.agent_type, task: data.task_id }),
        description: '',
        variant: 'default',
      };

    case 'agent_completed':
      if (!settings.notifyAgentActivity) return null;
      return {
        title: (data.success === 'true' ? '✅ ' : '❌ ') +
          (data.success === 'true'
            ? t('notifications.agentCompleted', { agent: data.agent_type, task: data.task_id })
            : t('notifications.agentFailed', { agent: data.agent_type, task: data.task_id })),
        description: '',
        variant: data.success === 'true' ? 'default' : 'destructive',
      };

    case 'conflict_detected':
      if (!settings.notifyConflicts) return null;
      return {
        title: '⚠️ ' + t('notifications.conflictDetected', { task: data.task_id }),
        description: '',
        variant: 'destructive',
      };

    case 'task_moved':
      return {
        title: t('notifications.taskMoved', {
          user: event.senderId,
          task: data.task_id,
          from: data.from_column,
          to: data.to_column,
        }),
        description: '',
        variant: 'default',
      };

    default:
      return null;
  }
}
