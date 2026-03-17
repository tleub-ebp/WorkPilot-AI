import { create } from 'zustand';
import type {
  ArenaBattle,
  ArenaBattleStatus,
  ArenaAnalytics,
  ArenaLabel,
  ArenaParticipant,
  ArenaTaskType,
  ArenaBattleProgressEvent,
  ArenaBattleResultEvent,
  ArenaBattleCompleteEvent,
} from '@shared/types/arena';

// ─── Store State ────────────────────────────────────────────────────────────

interface ArenaState {
  isOpen: boolean;

  /** Current battle being run or voted on */
  activeBattle: ArenaBattle | null;

  /** All historical battles */
  battles: ArenaBattle[];

  /** Analytics aggregated from all votes */
  analytics: ArenaAnalytics | null;

  /** Loading states */
  isStartingBattle: boolean;
  isLoadingHistory: boolean;
  isLoadingAnalytics: boolean;

  /** Auto-routing enabled */
  autoRoutingEnabled: boolean;

  error: string | null;
}

// ─── Actions ─────────────────────────────────────────────────────────────────

interface ArenaActions {
  openDialog: () => void;
  closeDialog: () => void;

  setActiveBattle: (battle: ArenaBattle | null) => void;
  setBattles: (battles: ArenaBattle[]) => void;
  setAnalytics: (analytics: ArenaAnalytics) => void;
  setIsStartingBattle: (v: boolean) => void;
  setIsLoadingHistory: (v: boolean) => void;
  setIsLoadingAnalytics: (v: boolean) => void;
  setAutoRoutingEnabled: (v: boolean) => void;
  setError: (error: string | null) => void;

  /** Handle streaming chunk from a participant */
  handleBattleProgress: (event: ArenaBattleProgressEvent) => void;

  /** Handle individual participant completion */
  handleBattleResult: (event: ArenaBattleResultEvent) => void;

  /** Handle full battle completion */
  handleBattleComplete: (event: ArenaBattleCompleteEvent) => void;

  /** Update battle status */
  updateBattleStatus: (battleId: string, status: ArenaBattleStatus) => void;

  /** Submit a vote for a battle */
  submitVote: (battleId: string, winnerLabel: ArenaLabel) => void;

  /** Load battle history from main process */
  loadHistory: () => Promise<void>;

  /** Load analytics from main process */
  loadAnalytics: () => Promise<void>;
}

// ─── Initial State ────────────────────────────────────────────────────────────

const initialState: ArenaState = {
  isOpen: false,
  activeBattle: null,
  battles: [],
  analytics: null,
  isStartingBattle: false,
  isLoadingHistory: false,
  isLoadingAnalytics: false,
  autoRoutingEnabled: false,
  error: null,
};

// ─── Store ────────────────────────────────────────────────────────────────────

export const useArenaStore = create<ArenaState & ArenaActions>((set, get) => ({
  ...initialState,

  openDialog: () => set({ isOpen: true, error: null }),
  closeDialog: () => set({ isOpen: false }),

  setActiveBattle: (battle) => set({ activeBattle: battle }),
  setBattles: (battles) => set({ battles }),
  setAnalytics: (analytics) => set({ analytics }),
  setIsStartingBattle: (v) => set({ isStartingBattle: v }),
  setIsLoadingHistory: (v) => set({ isLoadingHistory: v }),
  setIsLoadingAnalytics: (v) => set({ isLoadingAnalytics: v }),
  setAutoRoutingEnabled: (v) => set({ autoRoutingEnabled: v }),
  setError: (error) => set({ error }),

  handleBattleProgress: (event) => {
    const { activeBattle } = get();
    if (!activeBattle || activeBattle.id !== event.battleId) return;

    const participants = activeBattle.participants.map((p): ArenaParticipant => {
      if (p.label !== event.label) return p;
      return {
        ...p,
        output: p.output + event.chunk,
        status: 'running',
        tokensUsed: event.tokensUsed ?? p.tokensUsed,
        costUsd: event.costUsd ?? p.costUsd,
      };
    });

    set({ activeBattle: { ...activeBattle, participants } });
  },

  handleBattleResult: (event) => {
    const { activeBattle } = get();
    if (!activeBattle || activeBattle.id !== event.battleId) return;

    const participants = activeBattle.participants.map((p): ArenaParticipant => {
      if (p.label !== event.label) return p;
      return {
        ...p,
        output: event.output,
        status: event.error ? 'error' : 'completed',
        tokensUsed: event.tokensUsed,
        costUsd: event.costUsd,
        durationMs: event.durationMs,
        error: event.error,
      };
    });

    set({ activeBattle: { ...activeBattle, participants } });
  },

  handleBattleComplete: (event) => {
    const { activeBattle } = get();
    if (!activeBattle || activeBattle.id !== event.battleId) return;

    const updatedBattle: ArenaBattle = {
      ...activeBattle,
      participants: event.participants,
      status: 'voting',
      completedAt: Date.now(),
    };

    set({ activeBattle: updatedBattle });
  },

  updateBattleStatus: (battleId, status) => {
    const { activeBattle } = get();
    if (activeBattle?.id === battleId) {
      set({ activeBattle: { ...activeBattle, status } });
    }
  },

  submitVote: async (battleId, winnerLabel) => {
    const { activeBattle } = get();
    if (!activeBattle || activeBattle.id !== battleId) return;

    const winner = activeBattle.participants.find((p) => p.label === winnerLabel);
    if (!winner) return;

    try {
      if (typeof globalThis.electronAPI?.arenaVote !== 'function') {
        set({ error: 'Arena API not available — please restart the application.' });
        return;
      }
      const result = await globalThis.electronAPI.arenaVote({
        battleId,
        winnerLabel,
        winnerProfileId: winner.profileId,
        taskType: activeBattle.taskType,
        votedAt: Date.now(),
      });

      if (result.success) {
        const updatedBattle: ArenaBattle = {
          ...activeBattle,
          status: 'completed',
          winnerLabel,
          votedAt: Date.now(),
          revealed: true,
        };

        const battles = [updatedBattle, ...get().battles.filter((b) => b.id !== battleId)];
        set({ activeBattle: updatedBattle, battles });

        // Refresh analytics after vote
        get().loadAnalytics();
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to submit vote' });
    }
  },

  loadHistory: async () => {
    set({ isLoadingHistory: true, error: null });
    try {
      if (typeof globalThis.electronAPI?.arenaGetBattles !== 'function') {
        return;
      }
      const result = await globalThis.electronAPI.arenaGetBattles();
      if (result.success && result.data) {
        set({ battles: result.data });
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to load history' });
    } finally {
      set({ isLoadingHistory: false });
    }
  },

  loadAnalytics: async () => {
    set({ isLoadingAnalytics: true });
    try {
      if (typeof globalThis.electronAPI?.arenaGetAnalytics !== 'function') {
        return;
      }
      const result = await globalThis.electronAPI.arenaGetAnalytics();
      if (result.success && result.data) {
        set({ analytics: result.data });
      }
    } catch {
      // Silently fail analytics
    } finally {
      set({ isLoadingAnalytics: false });
    }
  },
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

export const openArenaDialog = () => {
  useArenaStore.getState().openDialog();
};
