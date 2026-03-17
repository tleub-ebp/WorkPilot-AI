/**
 * Arena Mode — Blind A/B Model Comparison
 *
 * Allows running the same task against multiple AI models in parallel,
 * anonymizing results until the user votes, then accumulating stats
 * for data-driven auto-routing.
 */

export type ArenaTaskType = 'coding' | 'review' | 'test' | 'planning' | 'spec' | 'insights';

export type ArenaBattleStatus = 'idle' | 'running' | 'voting' | 'completed' | 'error';

export type ArenaParticipantStatus = 'waiting' | 'running' | 'completed' | 'error';

/** Anonymous label shown during the blind voting phase */
export type ArenaLabel = 'A' | 'B' | 'C' | 'D';

/** One contestant in an arena battle */
export interface ArenaParticipant {
  /** Anonymous display id (A, B, C…) — revealed after vote */
  label: ArenaLabel;
  /** Profile ID (hidden until vote is cast) */
  profileId: string;
  /** Human-readable model name (hidden until vote is cast) */
  modelName: string;
  /** Provider name (hidden until vote is cast) */
  provider: string;
  status: ArenaParticipantStatus;
  /** Streamed output text */
  output: string;
  /** Total tokens used */
  tokensUsed: number;
  /** Estimated cost in USD */
  costUsd: number;
  /** Duration in ms */
  durationMs: number;
  /** Error message if status === 'error' */
  error?: string;
}

/** A single arena battle */
export interface ArenaBattle {
  id: string;
  taskType: ArenaTaskType;
  prompt: string;
  participants: ArenaParticipant[];
  status: ArenaBattleStatus;
  createdAt: number;
  completedAt?: number;
  votedAt?: number;
  /** Label of the winner (set after vote) */
  winnerLabel?: ArenaLabel;
  /** Whether model identities have been revealed (post-vote) */
  revealed: boolean;
}

/** A single vote record */
export interface ArenaVote {
  battleId: string;
  taskType: ArenaTaskType;
  winnerLabel: ArenaLabel;
  winnerProfileId: string;
  votedAt: number;
  costSaved?: number;
}

/** Per-model stats aggregated across all votes */
export interface ArenaModelStats {
  profileId: string;
  modelName: string;
  provider: string;
  wins: number;
  losses: number;
  total: number;
  winRate: number;
  avgCostPerBattle: number;
  totalCostUsd: number;
  avgDurationMs: number;
  byTaskType: Partial<Record<ArenaTaskType, {
    wins: number;
    total: number;
    winRate: number;
    avgCostUsd: number;
  }>>;
}

/** Global analytics summary */
export interface ArenaAnalytics {
  totalBattles: number;
  totalVotes: number;
  byModel: ArenaModelStats[];
  autoRoutingRecommendations: Partial<Record<ArenaTaskType, {
    profileId: string;
    modelName: string;
    winRate: number;
    confidence: 'low' | 'medium' | 'high';
  }>>;
  lastUpdated: number;
}

/** Progress event from main process during a running battle */
export interface ArenaBattleProgressEvent {
  battleId: string;
  label: ArenaLabel;
  chunk: string;
  tokensUsed?: number;
  costUsd?: number;
}

/** Completion event from main process for a single participant */
export interface ArenaBattleResultEvent {
  battleId: string;
  label: ArenaLabel;
  output: string;
  tokensUsed: number;
  costUsd: number;
  durationMs: number;
  error?: string;
}

/** Full battle completed event */
export interface ArenaBattleCompleteEvent {
  battleId: string;
  participants: ArenaParticipant[];
}
