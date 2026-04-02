/**
 * Swarm Mode — Multi-Agent Parallel Execution
 *
 * Types for the swarm orchestration system that executes
 * subtasks in parallel waves with dependency analysis.
 */

// ─── Enums ──────────────────────────────────────────────────────────────────

export type SwarmPhase =
  | 'initializing'
  | 'analyzing_dependencies'
  | 'executing_wave'
  | 'merging_wave'
  | 'complete'
  | 'failed';

export type SubtaskState =
  | 'pending'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'retrying'
  | 'skipped';

// ─── Configuration ──────────────────────────────────────────────────────────

export interface SwarmConfig {
  maxParallelAgents: number;
  failFast: boolean;
  maxRetriesPerSubtask: number;
  mergeAfterEachWave: boolean;
  profileDistribution: 'round_robin' | 'least_loaded' | 'dedicated';
  enableAiMerge: boolean;
  dryRun: boolean;
}

export const DEFAULT_SWARM_CONFIG: SwarmConfig = {
  maxParallelAgents: 4,
  failFast: false,
  maxRetriesPerSubtask: 2,
  mergeAfterEachWave: true,
  profileDistribution: 'round_robin',
  enableAiMerge: true,
  dryRun: false,
};

// ─── Data Models ────────────────────────────────────────────────────────────

export interface SubtaskNode {
  id: string;
  phaseName: string;
  description: string;
  filesToModify: string[];
  filesToCreate: string[];
  dependsOn: string[];
  state: SubtaskState;
  waveIndex: number;
  worktreePath: string | null;
  error: string | null;
  retryCount: number;
  durationSeconds: number | null;
}

export interface Wave {
  index: number;
  subtaskIds: string[];
  state: SubtaskState;
  durationSeconds: number | null;
  mergeSuccess: boolean | null;
}

export interface SwarmStatus {
  phase: SwarmPhase;
  totalSubtasks: number;
  completedSubtasks: number;
  failedSubtasks: number;
  runningSubtasks: number;
  totalWaves: number;
  currentWave: number;
  waves: Wave[];
  nodes: Record<string, SubtaskNode>;
  progressPercent: number;
  durationSeconds: number;
  error: string | null;
  config: SwarmConfig;
}

export interface ParallelismStats {
  totalWaves: number;
  maxParallelism: number;
  avgParallelism: number;
  waveSizes: number[];
  totalSubtasks: number;
  speedupEstimate: number;
}

// ─── Events ─────────────────────────────────────────────────────────────────

export interface SwarmEvent {
  type: SwarmEventType;
  [key: string]: unknown;
}

export type SwarmEventType =
  | 'swarm_started'
  | 'swarm_complete'
  | 'swarm_failed'
  | 'swarm_cancelled'
  | 'swarm_skipped'
  | 'phase_changed'
  | 'analysis_complete'
  | 'wave_started'
  | 'wave_completed'
  | 'wave_merged'
  | 'wave_merge_failed'
  | 'subtask_started'
  | 'subtask_completed'
  | 'subtask_retrying'
  | 'subtask_log'
  | 'final_merge_started'
  | 'final_merge_complete';

export interface SwarmAnalysisEvent extends SwarmEvent {
  type: 'analysis_complete';
  totalSubtasks: number;
  totalWaves: number;
  parallelismStats: ParallelismStats;
  waves: Wave[];
}

export interface SwarmSubtaskEvent extends SwarmEvent {
  type: 'subtask_started' | 'subtask_completed' | 'subtask_retrying';
  subtaskId: string;
  description?: string;
  waveIndex?: number;
  success?: boolean;
  durationSeconds?: number;
  error?: string | null;
  attempt?: number;
  maxRetries?: number;
}

export interface SwarmWaveEvent extends SwarmEvent {
  type: 'wave_started' | 'wave_completed';
  waveIndex: number;
  subtaskIds?: string[];
  parallelism?: number;
  allSucceeded?: boolean;
  durationSeconds?: number;
  completed?: number;
  failed?: number;
}
