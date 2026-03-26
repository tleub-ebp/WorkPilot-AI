import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CalendarClock, Play, Link2, BarChart3, Plus } from 'lucide-react';
import { SettingsSection } from './SettingsSection';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ScheduledTaskEntry {
  id: string;
  name: string;
  cron: string;
  action: string;
  priority: number;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed';
  nextRun: string;
}

interface TaskChainEntry {
  name: string;
  tasks: string[];
  currentStep: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SchedulerSettings() {
  const { t } = useTranslation('settings');
  const [checkInterval, setCheckInterval] = useState(30);
  const [autoStart, setAutoStart] = useState(true);

  const [scheduledTasks] = useState<ScheduledTaskEntry[]>([
    { id: 'sched-1', name: t('tasks.sampleTasks.dailyScan.name'), cron: '0 22 * * *', action: 'security_scan', priority: 2, status: 'pending', nextRun: t('tasks.sampleTasks.dailyScan.nextRun') },
    { id: 'sched-2', name: t('tasks.sampleTasks.weeklyUpdate.name'), cron: '0 3 * * 1', action: 'update_deps', priority: 5, status: 'pending', nextRun: t('tasks.sampleTasks.weeklyUpdate.nextRun') },
    { id: 'sched-3', name: t('tasks.sampleTasks.hourlyLog.name'), cron: '0 * * * *', action: 'check_logs', priority: 8, status: 'paused', nextRun: '—' },
  ]);

  const [chains] = useState<TaskChainEntry[]>([
    { name: t('tasks.sampleTasks.ciPipeline'), tasks: ['Lint', 'Test', 'Build', 'Deploy'], currentStep: 0 },
  ]);

  const statusColor: Record<string, string> = {
    pending: 'bg-blue-500/15 text-blue-600',
    running: 'bg-green-500/15 text-green-600',
    paused: 'bg-amber-500/15 text-amber-600',
    completed: 'bg-emerald-500/15 text-emerald-600',
    failed: 'bg-red-500/15 text-red-600',
  };

  return (
    <SettingsSection
      title={t('tasks.title')}
      description={t('tasks.description')}
    >
      <div className="space-y-8">
        {/* Global Settings */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <CalendarClock className="h-4 w-4 text-primary" />
            {t('tasks.settings.title')}
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            {t('tasks.settings.description')}
          </p>
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-border p-3">
              <div>
                <p className="text-sm font-medium">{t('tasks.settings.autoStart.label')}</p>
                <p className="text-xs text-muted-foreground">{t('tasks.settings.autoStart.description')}</p>
              </div>
              <button type="button"
                onClick={() => setAutoStart(!autoStart)}
                className={cn(
                  'relative h-6 w-11 rounded-full transition-colors',
                  autoStart ? 'bg-primary' : 'bg-muted-foreground/30'
                )}
              >
                <span className={cn(
                  'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform',
                  autoStart ? 'translate-x-5.5 left-0' : 'left-0.5'
                )} />
              </button>
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label
                  // biome-ignore lint/a11y/noLabelWithoutControl: intentional
                  className="text-xs font-medium text-muted-foreground"
                >
                  {t('tasks.settings.checkInterval.label')}
                </label>
                <span className="text-xs font-mono tabular-nums text-foreground">{checkInterval}s</span>
              </div>
              <input
                type="range" min={5} max={120} step={5}
                value={checkInterval}
                onChange={(e) => setCheckInterval(Number(e.target.value))}
                className="w-full accent-primary"
              />
              <p className="text-[10px] text-muted-foreground">{t('tasks.settings.checkInterval.description')}</p>
            </div>
          </div>
        </div>

        {/* Scheduled Tasks */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-sm font-semibold flex items-center gap-2">
              <Play className="h-4 w-4 text-primary" />
              {t('tasks.title')}
            </h4>
            <button type="button" className="flex items-center gap-1 rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground">
              <Plus className="h-3 w-3" />
              {t('tasks.addTask')}
            </button>
          </div>
          <p className="text-xs text-muted-foreground mb-3">
            {t('tasks.description')}
          </p>
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">{t('tasks.table.task')}</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">{t('tasks.table.cron')}</th>
                  <th className="text-center px-3 py-2 font-medium text-muted-foreground">{t('tasks.table.priority')}</th>
                  <th className="text-center px-3 py-2 font-medium text-muted-foreground">{t('tasks.table.status')}</th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">{t('tasks.table.nextRun')}</th>
                </tr>
              </thead>
              <tbody>
                {scheduledTasks.map((task) => (
                  <tr key={task.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2 font-medium">{task.name}</td>
                    <td className="px-3 py-2 font-mono text-muted-foreground">{task.cron}</td>
                    <td className="px-3 py-2 text-center font-mono">{task.priority}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium', statusColor[task.status])}>
                        {t(`tasks.status.${task.status}`)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right text-muted-foreground">{task.nextRun}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Task Chains */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <Link2 className="h-4 w-4 text-primary" />
            {t('tasks.chains.title')}
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            {t('tasks.chains.description')}
          </p>
          <div className="space-y-3">
            {chains.map((chain) => (
              <div key={chain.name} className="rounded-md border border-border p-3">
                <p className="text-xs font-semibold text-foreground mb-2">{chain.name}</p>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {chain.tasks.map((task, taskIndex) => {
                    const isCompleted = taskIndex < chain.currentStep;
                    const isCurrent = taskIndex === chain.currentStep;
                    
                    let taskStyleClass = 'rounded px-2 py-0.5 text-[10px] font-mono';
                    if (isCompleted) {
                      taskStyleClass += ' bg-green-500/15 text-green-600 line-through';
                    } else if (isCurrent) {
                      taskStyleClass += ' bg-primary/15 text-primary font-medium';
                    } else {
                      taskStyleClass += ' bg-accent text-muted-foreground';
                    }
                    
                    return (
                      <span key={task} className="flex items-center gap-1.5">
                        <span className={cn(taskStyleClass)}>
                          {task}
                        </span>
                        {taskIndex < chain.tasks.length - 1 && <span className="text-muted-foreground text-xs">→</span>}
                      </span>
                    );
                  })}
                </div>
              </div>
            ))}
            {chains.length === 0 && (
              <div className="rounded-md border border-dashed border-border bg-muted/20 p-6 text-center">
                <Link2 className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">{t('tasks.chains.noChains')}</p>
              </div>
            )}
          </div>
        </div>

        {/* Cron Expression Help */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-primary" />
            {t('tasks.cronReference.title')}
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            {t('tasks.cronReference.description')}
          </p>
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">{t('tasks.cronReference.table.expression')}</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">{t('tasks.cronReference.table.description')}</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { expr: '0 22 * * *', desc: t('tasks.cronReference.examples.daily') },
                  { expr: '*/15 * * * *', desc: t('tasks.cronReference.examples.every15min') },
                  { expr: '0 3 * * 1', desc: t('tasks.cronReference.examples.weekly') },
                  { expr: '0 0 1 * *', desc: t('tasks.cronReference.examples.monthly') },
                  { expr: '0 9-17 * * 1-5', desc: t('tasks.cronReference.examples.workHours') },
                ].map((row) => (
                  <tr key={`cron-${row.expr}`} className="border-b border-border last:border-0">
                    <td className="px-3 py-1.5 font-mono">{row.expr}</td>
                    <td className="px-3 py-1.5 text-muted-foreground">{row.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}



