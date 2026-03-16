/**
 * Multi-Repo Orchestration Types
 *
 * Types for coordinating spec execution across multiple repositories.
 */

/** Overall orchestration status */
export type MultiRepoStatus =
  | 'pending'
  | 'analyzing'
  | 'planning'
  | 'executing'
  | 'creating_prs'
  | 'completed'
  | 'failed';

/** Per-repo execution status */
export type RepoExecutionStatus =
  | 'pending'
  | 'analyzing'
  | 'planning'
  | 'coding'
  | 'qa'
  | 'completed'
  | 'failed'
  | 'skipped';

/** A target repository in the orchestration */
export interface RepoTarget {
  id: string;
  repo: string; // "owner/repo" or local path
  displayName: string;
  localPath: string;
  pathScope?: string; // For monorepo packages
  isMonorepoPackage?: boolean;
}

/** Dependency type between repos */
export type RepoDependencyType =
  | 'package'
  | 'api'
  | 'shared_types'
  | 'database'
  | 'event'
  | 'monorepo_internal';

/** A dependency edge between two repos */
export interface RepoDependencyEdge {
  source: string; // repo that depends on target
  target: string; // repo being depended upon
  type: RepoDependencyType;
  details?: string;
}

/** A detected breaking change between repos */
export interface BreakingChange {
  sourceRepo: string;
  targetRepo: string;
  changeType: string;
  description: string;
  severity: 'warning' | 'error';
  filePath: string;
  suggestion: string;
}

/** Execution state for a single repo in the orchestration */
export interface RepoExecutionState {
  repo: string;
  status: RepoExecutionStatus;
  specId?: string;
  prUrl?: string;
  branchName?: string;
  progress: number; // 0-100
  currentPhase?: string;
  errorMessage?: string;
}

/** The dependency graph structure */
export interface RepoDependencyGraph {
  nodes: string[];
  edges: RepoDependencyEdge[];
}

/** Full orchestration state */
export interface MultiRepoOrchestration {
  id: string;
  taskDescription: string;
  status: MultiRepoStatus;
  repos: RepoTarget[];
  dependencyGraph: RepoDependencyGraph;
  executionOrder: string[];
  repoStates: RepoExecutionState[];
  masterSpecDir: string;
  breakingChanges: BreakingChange[];
  overallProgress: number; // 0-100
  createdAt: string;
  updatedAt: string;
}

/** Progress update from the backend orchestrator */
export interface MultiRepoProgress {
  orchestrationId: string;
  status: MultiRepoStatus;
  currentRepo?: string;
  repoStates: RepoExecutionState[];
  message?: string;
  overallProgress: number; // 0-100
}

/** Configuration for creating a new multi-repo orchestration */
export interface MultiRepoCreateConfig {
  repos: Array<{
    repo: string;
    localPath: string;
    pathScope?: string;
  }>;
  taskDescription: string;
}
