/**
 * Continuous AI — Always-On Background Daemon
 *
 * Types for the proactive AI daemon that monitors CI/CD failures,
 * dependency vulnerabilities, new issues, and external PRs.
 */

// ─── Module States ──────────────────────────────────────────────────────────

export type ModuleState = 'disabled' | 'idle' | 'polling' | 'acting' | 'error' | 'cooldown';

export type ModuleName = 'cicd_watcher' | 'dependency_sentinel' | 'issue_responder' | 'pr_reviewer';

export type ActionType =
  | 'cicd_fix'
  | 'dependency_patch'
  | 'issue_triage'
  | 'issue_investigation'
  | 'pr_review'
  | 'pr_auto_approve';

export type ActionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'needs_approval';

// ─── Configurations ─────────────────────────────────────────────────────────

export interface DaemonModuleConfig {
  enabled: boolean;
  pollIntervalSeconds: number;
  autoAct: boolean;
  maxActionsPerHour: number;
  quietHoursStart: string;
  quietHoursEnd: string;
}

export interface CICDWatcherConfig extends DaemonModuleConfig {
  autoFix: boolean;
  autoCreatePr: boolean;
  watchedWorkflows: string[];
}

export interface DependencySentinelConfig extends DaemonModuleConfig {
  autoPatchMinor: boolean;
  autoPatchMajor: boolean;
  scanIntervalSeconds: number;
  packageManagers: string[];
}

export interface IssueResponderConfig extends DaemonModuleConfig {
  autoTriage: boolean;
  autoInvestigateBugs: boolean;
  autoCreateSpecs: boolean;
  labelsToWatch: string[];
}

export interface PRReviewerConfig extends DaemonModuleConfig {
  autoApproveTrivial: boolean;
  reviewExternalOnly: boolean;
  postReviewComments: boolean;
  trivialPatterns: string[];
}

export interface ContinuousAIConfig {
  enabled: boolean;
  dailyBudgetUsd: number;
  cicdWatcher: CICDWatcherConfig;
  dependencySentinel: DependencySentinelConfig;
  issueResponder: IssueResponderConfig;
  prReviewer: PRReviewerConfig;
}

// ─── Default Config ─────────────────────────────────────────────────────────

export const DEFAULT_CONTINUOUS_AI_CONFIG: ContinuousAIConfig = {
  enabled: false,
  dailyBudgetUsd: 5,
  cicdWatcher: {
    enabled: false,
    pollIntervalSeconds: 300,
    autoAct: false,
    maxActionsPerHour: 5,
    quietHoursStart: '',
    quietHoursEnd: '',
    autoFix: false,
    autoCreatePr: false,
    watchedWorkflows: [],
  },
  dependencySentinel: {
    enabled: false,
    pollIntervalSeconds: 86400,
    autoAct: false,
    maxActionsPerHour: 3,
    quietHoursStart: '',
    quietHoursEnd: '',
    autoPatchMinor: true,
    autoPatchMajor: false,
    scanIntervalSeconds: 86400,
    packageManagers: ['npm', 'pip'],
  },
  issueResponder: {
    enabled: false,
    pollIntervalSeconds: 180,
    autoAct: false,
    maxActionsPerHour: 10,
    quietHoursStart: '',
    quietHoursEnd: '',
    autoTriage: true,
    autoInvestigateBugs: false,
    autoCreateSpecs: false,
    labelsToWatch: [],
  },
  prReviewer: {
    enabled: false,
    pollIntervalSeconds: 300,
    autoAct: false,
    maxActionsPerHour: 5,
    quietHoursStart: '',
    quietHoursEnd: '',
    autoApproveTrivial: false,
    reviewExternalOnly: true,
    postReviewComments: true,
    trivialPatterns: ['docs', 'typo', 'readme', 'changelog'],
  },
};

// ─── Runtime State ──────────────────────────────────────────────────────────

export interface DaemonAction {
  id: string;
  module: ModuleName;
  actionType: ActionType;
  status: ActionStatus;
  title: string;
  description: string;
  target: string;
  createdAt: number;
  startedAt: number | null;
  completedAt: number | null;
  result: string | null;
  error: string | null;
  costUsd: number;
  durationSeconds: number | null;
  metadata: Record<string, unknown>;
}

export interface DaemonModuleStatus {
  name: ModuleName;
  state: ModuleState;
  lastPollAt: number | null;
  lastActionAt: number | null;
  actionsThisHour: number;
  totalActions: number;
  totalCostUsd: number;
  error: string | null;
}

export interface ContinuousAIStatus {
  running: boolean;
  startedAt: number | null;
  modules: Record<string, DaemonModuleStatus>;
  recentActions: DaemonAction[];
  totalCostTodayUsd: number;
  dailyBudgetUsd: number;
  enabledModulesCount: number;
  isOverBudget: boolean;
}

// ─── Events ─────────────────────────────────────────────────────────────────

export type DaemonEventType =
  | 'daemon_started'
  | 'daemon_stopped'
  | 'module_polling'
  | 'module_poll_complete'
  | 'module_error'
  | 'action_detected'
  | 'action_needs_approval'
  | 'action_completed'
  | 'action_rejected'
  | 'budget_exceeded';

export interface DaemonEvent {
  type: DaemonEventType;
  timestamp: number;
  [key: string]: unknown;
}
