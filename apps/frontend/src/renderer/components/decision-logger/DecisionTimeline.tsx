import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useDecisionLoggerStore, selectEntriesForTask } from '../../stores/decision-logger-store';
import type { DecisionEntry, DecisionType } from '../../../shared/types/decision-logger';

// ── Visual config ────────────────────────────────────────────────────────────

const TYPE_ICON: Record<DecisionType, string> = {
  tool_call:        '🔧',
  file_read:        '📖',
  file_write:       '✏️',
  reasoning:        '💭',
  decision:         '⚖️',
  phase_transition: '🔄',
  error_recovery:   '🩹',
};

const TYPE_COLOR: Record<DecisionType, string> = {
  tool_call:        'text-blue-400',
  file_read:        'text-slate-400',
  file_write:       'text-emerald-400',
  reasoning:        'text-purple-400',
  decision:         'text-amber-400',
  phase_transition: 'text-cyan-400',
  error_recovery:   'text-red-400',
};

const ALL_TYPES: DecisionType[] = [
  'tool_call', 'file_read', 'file_write', 'reasoning',
  'decision', 'phase_transition', 'error_recovery',
];

// ── Entry detail ─────────────────────────────────────────────────────────────

function EntryDetail({ entry }: Readonly<{ entry: DecisionEntry }>) {
  if (entry.decision_type === 'decision' && entry.alternatives?.length) {
    return (
      <div className="mt-1 text-xs text-muted-foreground space-y-0.5">
        {entry.alternatives.map((alt) => (
          <div
            key={alt}
            className={`flex items-center gap-1 ${alt === entry.selected ? 'text-emerald-400' : ''}`}
          >
            <span>{alt === entry.selected ? '✓' : '·'}</span>
            <span>{alt}</span>
          </div>
        ))}
      </div>
    );
  }
  if (entry.decision_type === 'phase_transition') {
    return (
      <div className="mt-1 text-xs text-muted-foreground">
        {entry.phase_from} → {entry.phase_to}
      </div>
    );
  }
  if (entry.decision_type === 'error_recovery' && entry.recovery_approach) {
    return (
      <div className="mt-1 text-xs text-muted-foreground italic">{entry.recovery_approach}</div>
    );
  }
  if (
    entry.decision_type === 'reasoning' &&
    entry.reasoning_text &&
    entry.reasoning_text !== entry.summary
  ) {
    return (
      <div className="mt-1 text-xs text-muted-foreground italic line-clamp-3">
        {entry.reasoning_text}
      </div>
    );
  }
  return null;
}

// ── Timeline row ─────────────────────────────────────────────────────────────

function TimelineRow({ entry }: Readonly<{ entry: DecisionEntry }>) {
  const icon  = TYPE_ICON[entry.decision_type]  ?? '•';
  const color = TYPE_COLOR[entry.decision_type] ?? 'text-foreground';
  const time  = new Date(entry.timestamp).toLocaleTimeString([], {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  return (
    <div className="flex gap-2 py-1.5 border-b border-border/30 last:border-0 group">
      <div className="flex flex-col items-center pt-0.5 shrink-0">
        <span className="text-base leading-none">{icon}</span>
        <div className="w-px flex-1 bg-border/30 mt-1 min-h-[8px] group-last:hidden" />
      </div>

      <div className="flex-1 min-w-0 pb-1">
        <div className="flex items-baseline gap-2">
          <span className={`text-xs font-medium shrink-0 ${color}`}>
            {entry.decision_type.replace('_', '\u00a0')}
          </span>
          <span className="text-xs text-foreground/80 truncate">{entry.summary}</span>
          <span className="text-xs text-muted-foreground shrink-0 ml-auto">{time}</span>
        </div>
        {entry.subtask_id && (
          <div className="text-xs text-muted-foreground/60 mt-0.5">
            subtask: {entry.subtask_id}
          </div>
        )}
        <EntryDetail entry={entry} />
      </div>
    </div>
  );
}

// ── Filter chips ─────────────────────────────────────────────────────────────

interface FilterBarProps {
  visible: Set<DecisionType>;
  onToggle: (t: DecisionType) => void;
  onReset: () => void;
  totalCount: number;
}

function FilterBar({ visible, onToggle, onReset, totalCount }: Readonly<FilterBarProps>) {
  return (
    <div className="flex flex-wrap items-center gap-1 px-3 py-2 border-b border-border/50">
      {ALL_TYPES.map((t) => (
        <button
          key={t}
          type="button"
          onClick={() => onToggle(t)}
          className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
            visible.has(t)
              ? 'border-primary/60 bg-primary/10 text-primary'
              : 'border-border text-muted-foreground hover:border-border/80'
          }`}
        >
          {TYPE_ICON[t]} {t.replace('_', ' ')}
        </button>
      ))}
      <span className="text-xs text-muted-foreground ml-auto">{totalCount}</span>
      <button
        type="button"
        onClick={onReset}
        className="text-xs px-2 py-0.5 rounded-full border border-border text-muted-foreground hover:text-foreground"
      >
        all
      </button>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

interface DecisionTimelineProps {
  taskId: string;
  specDirPath?: string;
  specId?: string;
  maxHeightClass?: string;
}

export function DecisionTimeline({
  taskId,
  specDirPath,
  specId,
  maxHeightClass = 'max-h-[480px]',
}: Readonly<DecisionTimelineProps>) {
  const { t } = useTranslation(['tasks']);
  const store = useDecisionLoggerStore();
  const entries = selectEntriesForTask(store, taskId);
  const bottomRef = useRef<HTMLDivElement>(null);

  const [visibleTypes, setVisibleTypes] = useState<Set<DecisionType>>(
    () => new Set(ALL_TYPES),
  );

  // Subscribe to live entries forwarded over IPC
  useEffect(() => {
    const api = globalThis.electronAPI;
    if (!api?.onDecisionLogEntry) return;
    const unsub = api.onDecisionLogEntry((incomingTaskId: string, entry: DecisionEntry) => {
      if (incomingTaskId === taskId) {
        store.addLiveEntry(taskId, entry);
      }
    });
    return unsub;
  }, [taskId, store]);

  // Load persisted historical log when specDirPath is provided
  useEffect(() => {
    const api = globalThis.electronAPI;
    if (!specDirPath || !api?.getDecisionLog) return;
    store.setLoadingHistory(true);
    api
      .getDecisionLog(specDirPath, taskId, specId ?? taskId)
      .then((result) => {
        if (result.success && result.data) {
          store.setHistoricalEntries(taskId, result.data.entries);
        }
      })
      .finally(() => store.setLoadingHistory(false));
  }, [taskId, specDirPath, specId, store]);

  // Auto-scroll to bottom on new entries
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const toggleType = (t: DecisionType) =>
    setVisibleTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t); else next.add(t);
      return next;
    });

  const resetTypes = () => setVisibleTypes(new Set(ALL_TYPES));

  const filtered = entries.filter((e) => visibleTypes.has(e.decision_type));

  if (store.isLoadingHistory) {
    return (
      <div className="flex items-center justify-center py-8 text-muted-foreground text-sm gap-2">
        <span className="animate-spin">⏳</span>
        <span>{t('tasks:decisionLogger.loading', 'Loading decision log…')}</span>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground text-sm gap-2">
        <span className="text-2xl">🎯</span>
        <span>{t('tasks:decisionLogger.empty', 'No decisions recorded yet')}</span>
        <span className="text-xs">
          {t('tasks:decisionLogger.emptyHint', 'Decisions appear here while the agent is running.')}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col rounded-md border border-border/60 bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 bg-muted/30">
        <span className="text-xs font-semibold text-foreground">
          🎯 {t('tasks:decisionLogger.title', 'Decision Timeline')}
        </span>
        <span className="text-xs text-muted-foreground">
          {filtered.length}/{entries.length}
        </span>
      </div>

      {/* Filter bar */}
      <FilterBar
        visible={visibleTypes}
        onToggle={toggleType}
        onReset={resetTypes}
        totalCount={entries.length}
      />

      {/* Scroll area */}
      <div className={`overflow-y-auto ${maxHeightClass} px-3`}>
        {filtered.length === 0 ? (
          <div className="py-6 text-center text-xs text-muted-foreground">
            {t('tasks:decisionLogger.noMatch', 'No entries match the current filter.')}
          </div>
        ) : (
          filtered.map((entry) => (
            <TimelineRow key={`${entry.session_id}-${entry.id}`} entry={entry} />
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

export default DecisionTimeline;
