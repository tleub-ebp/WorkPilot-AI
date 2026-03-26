import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Swords,
  Trophy,
  BarChart3,
  History,
  CheckCircle2,
  Loader2,
  X,
  ChevronRight,
  TrendingUp,
  Route,
  AlertCircle,
  Trash2,
} from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui';
import { cn } from '@/lib/utils';

import { useArenaStore } from '@/stores/arena-store';
import { useProjectStore } from '@/stores/project-store';
import type { ArenaTaskType, ArenaBattle, ArenaLabel, ArenaParticipant } from '@shared/types/arena';

// â”€â”€â”€ Constants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const TASK_TYPES: { value: ArenaTaskType; labelKey: string; icon: string }[] = [
  { value: 'coding', labelKey: 'arena:taskTypes.coding', icon: 'ðŸ’»' },
  { value: 'review', labelKey: 'arena:taskTypes.review', icon: 'ðŸ”' },
  { value: 'test', labelKey: 'arena:taskTypes.test', icon: 'ðŸ§ª' },
  { value: 'planning', labelKey: 'arena:taskTypes.planning', icon: 'ðŸ“‹' },
  { value: 'spec', labelKey: 'arena:taskTypes.spec', icon: 'ðŸ“' },
  { value: 'insights', labelKey: 'arena:taskTypes.insights', icon: 'ðŸ’¡' },
];

const LABEL_COLORS: Record<ArenaLabel, string> = {
  A: 'bg-blue-500/20 text-blue-400 border-blue-500/40',
  B: 'bg-purple-500/20 text-purple-400 border-purple-500/40',
  C: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40',
  D: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
};

const DEMO_PROFILES = [
  { id: 'claude-sonnet', name: 'Claude Sonnet 4.6', model: 'claude-sonnet-4-6' },
  { id: 'claude-haiku', name: 'Claude Haiku 4.5', model: 'claude-haiku-4-5-20251001' },
  { id: 'gpt-4.1', name: 'GPT-4.1', model: 'gpt-4.1' },
  { id: 'gpt-4.1-mini', name: 'GPT-4.1 Mini', model: 'gpt-4.1-mini' },
];

const CONFIDENCE_COLOR: Record<string, string> = {
  low: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  high: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
};

const ARENA_TABS = [
  { id: 'battle' as ArenaTab, icon: Swords, labelKey: 'tabs.battle' },
  { id: 'history' as ArenaTab, icon: History, labelKey: 'tabs.history' },
  { id: 'analytics' as ArenaTab, icon: BarChart3, labelKey: 'tabs.analytics' },
  { id: 'routing' as ArenaTab, icon: Route, labelKey: 'tabs.routing' },
];

// â”€â”€â”€ Tab types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

type ArenaTab = 'battle' | 'history' | 'analytics' | 'routing';

// â”€â”€â”€ Sub-components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function ParticipantCard({
  participant,
  battle,
  onVote,
  canVote,
}: {
  readonly participant: ArenaParticipant;
  readonly battle: ArenaBattle;
  readonly onVote: (label: ArenaLabel) => void;
  readonly canVote: boolean;
}) {
  const { t } = useTranslation('arena');
  const isWinner = battle.winnerLabel === participant.label;
  const isRevealed = battle.revealed;

  const getDisplayText = () => {
    if (participant.status === 'waiting') {
      return t('battle.waitingForStart');
    }
    if (participant.status === 'running') {
      return t('battle.generating');
    }
    return participant.error || t('battle.noOutput');
  };

  return (
    <>
      {/* biome-ignore lint/a11y/noNoninteractiveElementInteractions: interactive handler is intentional */}
      {/* biome-ignore lint/a11y/noStaticElementInteractions: interactive handler is intentional */}
      {/* biome-ignore lint/a11y/useAriaPropsSupportedByRole: ARIA attributes are valid for this role  */}
      <div
        role={canVote ? 'button' : undefined}
        tabIndex={canVote ? 0 : undefined}
        className={cn(
          'flex flex-col rounded-xl border transition-all duration-300 text-left',
          isWinner && isRevealed
            ? 'border-yellow-500/60 bg-yellow-500/5 shadow-lg shadow-yellow-500/10'
            : 'border-border bg-card',
          canVote && 'cursor-pointer hover:border-primary/50 hover:bg-accent/30',
          !canVote && 'cursor-default'
        )}
        onClick={() => canVote && onVote(participant.label)}
      onKeyDown={(e) => canVote && (e.key === 'Enter' || e.key === ' ') && onVote(participant.label)}
      aria-label={canVote ? `${t('battle.model')} ${participant.label}. ${isWinner && isRevealed ? t('battle.winner') : ''}` : undefined}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={cn('font-bold text-sm px-2', LABEL_COLORS[participant.label])}
          >
            {t('battle.model')} {participant.label}
          </Badge>
          {isRevealed && (
            <span className="text-xs text-muted-foreground">
              {participant.modelName}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {participant.status === 'running' && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          )}
          {participant.status === 'completed' && (
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
          )}
          {participant.status === 'error' && (
            <AlertCircle className="h-3.5 w-3.5 text-destructive" />
          )}
          {isWinner && isRevealed && (
            <Trophy className="h-4 w-4 text-yellow-500" />
          )}
        </div>
      </div>

      {/* Output */}
      <ScrollArea className="flex-1 max-h-64">
        <div className="p-3 text-sm font-mono whitespace-pre-wrap text-foreground/90 min-h-[120px]">
          {participant.output || (
            <span className="text-muted-foreground italic">
              {getDisplayText()}
            </span>
          )}
          {participant.status === 'running' && (
            <span className="inline-block w-1.5 h-4 bg-primary animate-pulse ml-0.5 align-middle" />
          )}
        </div>
      </ScrollArea>

      {/* Footer stats */}
      <div className="flex items-center justify-between px-3 py-2 border-t border-border text-xs text-muted-foreground">
        <span>{participant.tokensUsed > 0 ? `${participant.tokensUsed.toLocaleString()} tokens` : 'â€”'}</span>
        <span>{participant.costUsd > 0 ? `$${participant.costUsd.toFixed(5)}` : 'â€”'}</span>
        <span>{participant.durationMs > 0 ? `${(participant.durationMs / 1000).toFixed(1)}s` : 'â€”'}</span>
      </div>

      {/* Vote button */}
      {canVote && (
        <div className="px-3 pb-3">
          <Button
            variant="outline"
            size="sm"
            className="w-full gap-2 hover:bg-primary hover:text-primary-foreground transition-colors"
            onClick={(e) => { e.stopPropagation(); onVote(participant.label); }}
          >
            <Trophy className="h-3.5 w-3.5" />
            {t('battle.voteForThis')}
          </Button>
        </div>
      )}
    </div>
    </>
  );
}

// â”€â”€â”€ Battle Tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function BattleTab() {
  const { t } = useTranslation('arena');
  const { activeBattle, isStartingBattle, error, setIsStartingBattle, setActiveBattle, setError, submitVote, handleBattleProgress, handleBattleResult, handleBattleComplete } = useArenaStore();
  const selectedProject = useProjectStore((s) => s.projects.find((p) => p.id === s.selectedProjectId));

  const [taskType, setTaskType] = useState<ArenaTaskType>('coding');
  const [prompt, setPrompt] = useState('');
  const [selectedProfiles, setSelectedProfiles] = useState<string[]>(['profile-1', 'profile-2']);
  const [profiles, setProfiles] = useState<Array<{ id: string; name: string; model: string }>>([]);

  // Load profiles on mount
  useEffect(() => {
    const loadProfiles = async () => {
      try {
        if (typeof globalThis.electronAPI?.arenaGetProfiles !== 'function') {
          // Preload not yet reloaded â€” use demo profiles
          setProfiles(DEMO_PROFILES);
          setSelectedProfiles([DEMO_PROFILES[0].id, DEMO_PROFILES[1].id]);
          return;
        }
        const res = await globalThis.electronAPI.arenaGetProfiles();
        if (res.success && Array.isArray(res.data) && res.data.length > 0) {
          setProfiles(res.data as Array<{ id: string; name: string; model: string }>);
          setSelectedProfiles((res.data as Array<{ id: string }>).slice(0, 2).map((p) => p.id));
        } else {
          setProfiles(DEMO_PROFILES);
          setSelectedProfiles([DEMO_PROFILES[0].id, DEMO_PROFILES[1].id]);
        }
      } catch {
        setProfiles(DEMO_PROFILES);
        setSelectedProfiles([DEMO_PROFILES[0].id, DEMO_PROFILES[1].id]);
      }
    };
    loadProfiles();
  }, []);

  // Subscribe to battle events (only when API is available)
  useEffect(() => {
    const api = globalThis.electronAPI;
    if (
      typeof api?.onArenaBattleProgress !== 'function' ||
      typeof api?.onArenaBattleResult !== 'function' ||
      typeof api?.onArenaBattleComplete !== 'function' ||
      typeof api?.onArenaBattleError !== 'function'
    ) {
      return;
    }
    const c1 = api.onArenaBattleProgress(handleBattleProgress);
    const c2 = api.onArenaBattleResult(handleBattleResult);
    const c3 = api.onArenaBattleComplete(handleBattleComplete);
    const c4 = api.onArenaBattleError(({ error: err }: { battleId: string; error: string }) => setError(err));

    return () => [c1, c2, c3, c4].forEach((c) => c());
  }, [handleBattleProgress, handleBattleResult, handleBattleComplete, setError]);

  const handleStartBattle = useCallback(async () => {
    if (!prompt.trim() || selectedProfiles.length < 2) return;

    setIsStartingBattle(true);
    setError(null);

    try {
      if (typeof globalThis.electronAPI?.arenaStartBattle !== 'function') {
        setError('Arena API not available â€” please restart the application.');
        return;
      }
      const result = await globalThis.electronAPI.arenaStartBattle({
        taskType,
        prompt: prompt.trim(),
        profileIds: selectedProfiles,
        projectPath: selectedProject?.path,
      });

      if (result.success && result.data) {
        setActiveBattle(result.data);
      } else {
        setError(result.error ?? t('errors.startFailed'));
      }
    } finally {
      setIsStartingBattle(false);
    }
  }, [prompt, selectedProfiles, taskType, selectedProject, setIsStartingBattle, setActiveBattle, setError, t]);

  const toggleProfile = (id: string) => {
    setSelectedProfiles((prev) => {
      if (prev.includes(id)) {
        if (prev.length <= 2) return prev;
        return prev.filter((p) => p !== id);
      }
      if (prev.length >= 4) return prev;
      return [...prev, id];
    });
  };

  const canVote = activeBattle?.status === 'voting';
  const isRunning = activeBattle?.status === 'running';

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Config panel â€” only show when not in a battle */}
      {!activeBattle && (
        <div className="flex flex-col gap-4 p-4 rounded-xl border border-border bg-card">
          {/* Task type */}
          <div>
            // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
            <label className="text-sm font-medium mb-2 block text-foreground">{t('battle.taskType')}</label>
            <div className="flex flex-wrap gap-2">
              {TASK_TYPES.map((tt) => (
                <button
                  type="button"
                  key={tt.value}
                  onClick={() => setTaskType(tt.value)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border transition-all',
                    taskType === tt.value
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:border-primary/50 hover:bg-accent/50'
                  )}
                >
                  <span>{tt.icon}</span>
                  <span>{t(tt.labelKey)}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Model selection */}
          <div>
            // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
            <label className="text-sm font-medium mb-2 block text-foreground">
              {t('battle.selectModels')}
              <span className="ml-1.5 text-xs text-muted-foreground">({t('battle.selectModelHint')})</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {profiles.map((p) => (
                <button type="button"
                  key={p.id}
                  onClick={() => toggleProfile(p.id)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border transition-all',
                    selectedProfiles.includes(p.id)
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:border-primary/50 hover:bg-accent/50'
                  )}
                >
                  {selectedProfiles.includes(p.id) && (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  )}
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          {/* Prompt */}
          <div>
            // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
            <label className="text-sm font-medium mb-2 block text-foreground">{t('battle.prompt')}</label>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={t('battle.promptPlaceholder')}
              className="min-h-[100px] resize-none font-mono text-sm"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-sm text-destructive p-2 rounded-lg bg-destructive/10">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <Button
            onClick={handleStartBattle}
            disabled={!prompt.trim() || selectedProfiles.length < 2 || isStartingBattle}
            className="gap-2"
          >
            {isStartingBattle ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Swords className="h-4 w-4" />
            )}
            {t('battle.startBattle')}
          </Button>
        </div>
      )}

      {/* Battle arena */}
      {activeBattle && (
        <div className="flex flex-col gap-3 flex-1">
          {/* Battle header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="gap-1">
                {TASK_TYPES.find((t) => t.value === activeBattle.taskType)?.icon}
                {t(`taskTypes.${activeBattle.taskType}`)}
              </Badge>
              {isRunning && (
                <Badge variant="outline" className="gap-1 text-primary border-primary/50 bg-primary/10">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  {t('battle.statusRunning')}
                </Badge>
              )}
              {canVote && (
                <Badge variant="outline" className="gap-1 text-yellow-500 border-yellow-500/50 bg-yellow-500/10">
                  <Trophy className="h-3 w-3" />
                  {t('battle.statusVoting')}
                </Badge>
              )}
              {activeBattle.status === 'completed' && (
                <Badge variant="outline" className="gap-1 text-emerald-500 border-emerald-500/50 bg-emerald-500/10">
                  <CheckCircle2 className="h-3 w-3" />
                  {t('battle.statusCompleted')}
                </Badge>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setActiveBattle(null); setError(null); }}
              className="gap-1.5 text-muted-foreground"
            >
              <X className="h-3.5 w-3.5" />
              {t('battle.newBattle')}
            </Button>
          </div>

          {/* Prompt display */}
          <div className="text-xs text-muted-foreground p-2 rounded-lg bg-muted/50 font-mono line-clamp-2">
            {activeBattle.prompt}
          </div>

          {/* Vote prompt */}
          {canVote && (
            <div className="flex items-center gap-2 p-3 rounded-xl border border-yellow-500/40 bg-yellow-500/5 text-sm text-yellow-400">
              <Trophy className="h-4 w-4 shrink-0" />
              <span>{t('battle.votePrompt')}</span>
            </div>
          )}

          {/* Revealed winner */}
          {activeBattle.status === 'completed' && activeBattle.revealed && activeBattle.winnerLabel && (
            <div className="flex items-center gap-2 p-3 rounded-xl border border-yellow-500/40 bg-yellow-500/5 text-sm">
              <Trophy className="h-4 w-4 text-yellow-500 shrink-0" />
              <span className="text-yellow-400">
                {t('battle.winner')}:{' '}
                <strong>
                  {activeBattle.participants.find((p) => p.label === activeBattle.winnerLabel)?.modelName ??
                    `Model ${activeBattle.winnerLabel}`}
                </strong>
              </span>
            </div>
          )}

          {/* Participant grid */}
          <div className="grid gap-3 flex-1 grid-cols-2">
            {activeBattle.participants.map((p) => (
              <ParticipantCard
                key={p.label}
                participant={p}
                battle={activeBattle}
                onVote={(label) => submitVote(activeBattle.id, label)}
                canVote={canVote}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// â”€â”€â”€ History Tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function HistoryTab() {
  const { t } = useTranslation('arena');
  const { battles, isLoadingHistory, loadHistory } = useArenaStore();

  const arenaClearHistoryFn = useCallback(async () => {
    if (typeof globalThis.electronAPI?.arenaClearHistory === 'function') {
      await globalThis.electronAPI.arenaClearHistory();
    }
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  if (isLoadingHistory) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t('history.loading')}
      </div>
    );
  }

  if (battles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-muted-foreground gap-2">
        <History className="h-8 w-8 opacity-40" />
        <p className="text-sm">{t('history.empty')}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{battles.length} {t('history.battles')}</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={arenaClearHistoryFn}
          className="gap-1.5 text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {t('history.clearAll')}
        </Button>
      </div>

      <ScrollArea className="max-h-[500px]">
        <div className="flex flex-col gap-2 pr-2">
          {battles.map((battle) => (
            <BattleHistoryRow key={battle.id} battle={battle} />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

function BattleHistoryRow({ battle }: { readonly battle: ArenaBattle }) {
  const { t } = useTranslation('arena');
  const [expanded, setExpanded] = useState(false);
  const winner = battle.participants.find((p) => p.label === battle.winnerLabel);

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <button type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-accent/30 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-base">{TASK_TYPES.find((tt) => tt.value === battle.taskType)?.icon}</span>
          <span className="text-sm truncate">{battle.prompt.length > 60 ? `${battle.prompt.slice(0, 60)}â€¦` : battle.prompt}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {battle.status === 'completed' && winner && (
            <Badge variant="outline" className="gap-1 text-yellow-500 border-yellow-500/40">
              <Trophy className="h-3 w-3" />
              {winner.modelName}
            </Badge>
          )}
          {battle.status === 'voting' && (
            <Badge variant="outline" className="text-yellow-500 border-yellow-500/40">
              {t('history.awaitingVote')}
            </Badge>
          )}
          <ChevronRight className={cn('h-4 w-4 text-muted-foreground transition-transform', expanded && 'rotate-90')} />
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-1 grid grid-cols-2 gap-2 border-t border-border bg-muted/20 animate-in slide-in-from-top-2 duration-200">
          {battle.participants.map((p) => (
            <div key={p.label} className={cn('rounded-lg border p-2 text-xs', battle.winnerLabel === p.label ? 'border-yellow-500/50 bg-yellow-500/5' : 'border-border')}>
              <div className="flex items-center justify-between mb-1">
                <Badge variant="outline" className={cn('text-xs', LABEL_COLORS[p.label])}>
                  {t('battle.model')} {p.label}
                </Badge>
                {battle.winnerLabel === p.label && <Trophy className="h-3.5 w-3.5 text-yellow-500" />}
              </div>
              <p className="text-muted-foreground">{p.modelName}</p>
              <p className="font-mono text-muted-foreground/70 mt-0.5">
                {p.tokensUsed.toLocaleString()} tokens Â· ${p.costUsd.toFixed(5)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// â”€â”€â”€ Analytics Tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function AnalyticsTab() {
  const { t } = useTranslation('arena');
  const { analytics, isLoadingAnalytics, loadAnalytics } = useArenaStore();

  const getRankingStyle = (rank: number) => {
    if (rank === 0) {
      return 'bg-yellow-500/20 text-yellow-500';
    }
    if (rank === 1) {
      return 'bg-zinc-400/20 text-zinc-400';
    }
    return 'bg-orange-500/20 text-orange-400';
  };

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  if (isLoadingAnalytics) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t('analytics.loading')}
      </div>
    );
  }

  if (!analytics || analytics.totalVotes === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-muted-foreground gap-2">
        <BarChart3 className="h-8 w-8 opacity-40" />
        <p className="text-sm">{t('analytics.noData')}</p>
        <p className="text-xs opacity-60">{t('analytics.noDataHint')}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-border bg-card p-3 text-center">
          <p className="text-2xl font-bold text-foreground">{analytics.totalBattles}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{t('analytics.totalBattles')}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-3 text-center">
          <p className="text-2xl font-bold text-foreground">{analytics.totalVotes}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{t('analytics.totalVotes')}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-3 text-center">
          <p className="text-2xl font-bold text-foreground">{analytics.byModel.length}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{t('analytics.modelsCompared')}</p>
        </div>
      </div>

      {/* Model rankings */}
      <div>
        <h3 className="text-sm font-semibold mb-2 text-foreground">{t('analytics.modelRankings')}</h3>
        <div className="flex flex-col gap-2">
          {analytics.byModel.map((model, i) => (
            <div key={model.profileId} className="flex items-center gap-3 p-3 rounded-xl border border-border bg-card">
              <span className={cn(
                'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0',
                getRankingStyle(i)
              )}>
                {i + 1}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{model.modelName}</p>
                <p className="text-xs text-muted-foreground">{model.provider}</p>
              </div>
              <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0">
                <div className="text-center">
                  <p className="text-sm font-semibold text-foreground">{(model.winRate * 100).toFixed(0)}%</p>
                  <p>{t('analytics.winRate')}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-foreground">{model.wins}/{model.total}</p>
                  <p>{t('analytics.winsTotal')}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-foreground">${model.avgCostPerBattle.toFixed(4)}</p>
                  <p>{t('analytics.avgCost')}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// â”€â”€â”€ Auto-Routing Tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function RoutingTab() {
  const { t } = useTranslation('arena');
  const { analytics, autoRoutingEnabled, setAutoRoutingEnabled, loadAnalytics } = useArenaStore();

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  const recommendations = analytics?.autoRoutingRecommendations ?? {};
  const hasRecommendations = Object.keys(recommendations).length > 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Toggle */}
      <div className="flex items-center justify-between p-4 rounded-xl border border-border bg-card">
        <div className="flex items-center gap-3">
          <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', autoRoutingEnabled ? 'bg-primary/10' : 'bg-muted')}>
            <Route className={cn('h-5 w-5', autoRoutingEnabled ? 'text-primary' : 'text-muted-foreground')} />
          </div>
          <div>
            <p className="text-sm font-medium">{t('routing.autoRouting')}</p>
            <p className="text-xs text-muted-foreground">{t('routing.autoRoutingDesc')}</p>
          </div>
        </div>
        <button type="button"
          onClick={() => setAutoRoutingEnabled(!autoRoutingEnabled)}
          className={cn(
            'relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors',
            autoRoutingEnabled ? 'bg-primary' : 'bg-muted'
          )}
          role="switch"
          aria-checked={autoRoutingEnabled}
        >
          <span
            className={cn(
              'pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-lg ring-0 transition-transform',
              autoRoutingEnabled ? 'translate-x-5' : 'translate-x-0'
            )}
          />
        </button>
      </div>

      {hasRecommendations ? (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-foreground">{t('routing.recommendations')}</h3>
          {TASK_TYPES.map((tt) => {
            const rec = recommendations[tt.value];
            if (!rec) return null;
            return (
              <div key={tt.value} className="flex items-center justify-between p-3 rounded-xl border border-border bg-card">
                <div className="flex items-center gap-2">
                  <span>{tt.icon}</span>
                  <span className="text-sm">{t(`taskTypes.${tt.value}`)}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium">{rec.modelName}</span>
                  <Badge variant="outline" className={cn('text-xs', CONFIDENCE_COLOR[rec.confidence])}>
                    {(rec.winRate * 100).toFixed(0)}% Â· {t(`routing.confidence.${rec.confidence}`)}
                  </Badge>
                </div>
              </div>
            );
          }).filter(Boolean)}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-40 text-muted-foreground gap-2">
          <Route className="h-8 w-8 opacity-40" />
          <p className="text-sm">{t('routing.noRecommendations')}</p>
          <p className="text-xs opacity-60">{t('routing.noRecommendationsHint')}</p>
        </div>
      )}

      {analytics && analytics.totalVotes < 10 && (
        <div className="flex items-start gap-2 text-xs text-muted-foreground p-3 rounded-xl bg-muted/50">
          <TrendingUp className="h-3.5 w-3.5 shrink-0 mt-0.5" />
          <span>{t('routing.needMoreData', { count: 10 - analytics.totalVotes })}</span>
        </div>
      )}
    </div>
  );
}

// â”€â”€â”€ Main Dialog â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export function ArenaDialog() {
  const { t } = useTranslation('arena');
  const { isOpen, closeDialog } = useArenaStore();
  const [activeTab, setActiveTab] = useState<ArenaTab>('battle');


  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeDialog()}>
      <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col p-0 gap-0 overflow-hidden">
        <DialogHeader className="shrink-0 p-5 pb-0">
          <DialogTitle className="flex items-center gap-2.5 text-xl">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <Swords className="h-5 w-5 text-primary" />
            </div>
            <span>{t('title')}</span>
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground mt-0.5">
            {t('subtitle')}
          </DialogDescription>
        </DialogHeader>

        {/* Tab navigation */}
        <div className="flex gap-1 px-5 pt-4 border-b border-border pb-0 shrink-0">
          {ARENA_TABS.map(({ id, icon: Icon, labelKey }) => (
            <button type="button"
              key={id}
              onClick={() => setActiveTab(id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 text-sm rounded-t-lg border-b-2 transition-all duration-200',
                activeTab === id
                  ? 'border-primary text-primary bg-primary/5'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-accent/50'
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {t(labelKey)}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <ScrollArea className="flex-1 overflow-auto">
          <div className="p-5">
            {activeTab === 'battle' && <BattleTab />}
            {activeTab === 'history' && <HistoryTab />}
            {activeTab === 'analytics' && <AnalyticsTab />}
            {activeTab === 'routing' && <RoutingTab />}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}



