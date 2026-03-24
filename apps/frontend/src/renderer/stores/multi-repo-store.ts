import { create } from 'zustand';
import type {
  MultiRepoOrchestration,
  MultiRepoStatus,
  RepoTarget,
  RepoExecutionState,
  RepoDependencyGraph,
  BreakingChange,
} from '@shared/types';

interface MultiRepoState {
  // Dialog state
  isDialogOpen: boolean;

  // Active orchestration
  activeOrchestration: MultiRepoOrchestration | null;
  orchestrations: MultiRepoOrchestration[];

  // Configuration (dialog form state)
  targetRepos: RepoTarget[];
  taskDescription: string;

  // Execution state
  status: MultiRepoStatus;
  repoStates: RepoExecutionState[];
  dependencyGraph: RepoDependencyGraph | null;
  executionOrder: string[];
  breakingChanges: BreakingChange[];
  overallProgress: number;
  currentRepo: string | null;
  statusMessage: string;

  // Loading states
  isCreating: boolean;
  isStarting: boolean;

  // Actions - Dialog
  openDialog: () => void;
  closeDialog: () => void;

  // Actions - Repo configuration
  addRepo: (repo: RepoTarget) => void;
  removeRepo: (repoId: string) => void;
  updateRepo: (repoId: string, updates: Partial<RepoTarget>) => void;
  setTaskDescription: (desc: string) => void;

  // Actions - Orchestration lifecycle
  setActiveOrchestration: (orch: MultiRepoOrchestration | null) => void;
  setOrchestrations: (orchs: MultiRepoOrchestration[]) => void;
  setIsCreating: (val: boolean) => void;
  setIsStarting: (val: boolean) => void;

  // Actions - Execution updates (from IPC events)
  setStatus: (status: MultiRepoStatus) => void;
  setStatusMessage: (message: string) => void;
  updateRepoState: (repo: string, state: Partial<RepoExecutionState>) => void;
  setDependencyGraph: (graph: RepoDependencyGraph) => void;
  setExecutionOrder: (order: string[]) => void;
  addBreakingChange: (change: BreakingChange) => void;
  setOverallProgress: (progress: number) => void;
  setCurrentRepo: (repo: string | null) => void;

  // Actions - Reset
  reset: () => void;
  resetForm: () => void;
}

const initialFormState = {
  targetRepos: [] as RepoTarget[],
  taskDescription: '',
};

const initialExecutionState = {
  status: 'pending' as MultiRepoStatus,
  repoStates: [] as RepoExecutionState[],
  dependencyGraph: null as RepoDependencyGraph | null,
  executionOrder: [] as string[],
  breakingChanges: [] as BreakingChange[],
  overallProgress: 0,
  currentRepo: null as string | null,
  statusMessage: '',
};

export const useMultiRepoStore = create<MultiRepoState>((set) => ({
  // Initial state
  isDialogOpen: false,
  activeOrchestration: null,
  orchestrations: [],
  ...initialFormState,
  ...initialExecutionState,
  isCreating: false,
  isStarting: false,

  // Dialog
  openDialog: () => set({ isDialogOpen: true }),
  closeDialog: () => set({ isDialogOpen: false }),

  // Repo configuration
  addRepo: (repo) =>
    set((state) => ({
      targetRepos: [...state.targetRepos, repo],
    })),

  removeRepo: (repoId) =>
    set((state) => ({
      targetRepos: state.targetRepos.filter((r) => r.id !== repoId),
    })),

  updateRepo: (repoId, updates) =>
    set((state) => ({
      targetRepos: state.targetRepos.map((r) =>
        r.id === repoId ? { ...r, ...updates } : r
      ),
    })),

  setTaskDescription: (desc) => set({ taskDescription: desc }),

  // Orchestration lifecycle
  setActiveOrchestration: (orch) =>
    set({
      activeOrchestration: orch,
      ...(orch
        ? {
            status: orch.status,
            repoStates: orch.repoStates,
            dependencyGraph: orch.dependencyGraph,
            executionOrder: orch.executionOrder,
            breakingChanges: orch.breakingChanges,
            overallProgress: orch.overallProgress,
          }
        : {}),
    }),

  setOrchestrations: (orchs) => set({ orchestrations: orchs }),
  setIsCreating: (val) => set({ isCreating: val }),
  setIsStarting: (val) => set({ isStarting: val }),

  // Execution updates
  setStatus: (status) => set({ status }),
  setStatusMessage: (message) => set({ statusMessage: message }),

  updateRepoState: (repo, updates) =>
    set((state) => ({
      repoStates: state.repoStates.some((rs) => rs.repo === repo)
        ? state.repoStates.map((rs) =>
            rs.repo === repo ? { ...rs, ...updates } : rs
          )
        : [
            ...state.repoStates,
            { repo, status: 'pending', progress: 0, ...updates } as RepoExecutionState,
          ],
    })),

  setDependencyGraph: (graph) => set({ dependencyGraph: graph }),
  setExecutionOrder: (order) => set({ executionOrder: order }),

  addBreakingChange: (change) =>
    set((state) => ({
      breakingChanges: [...state.breakingChanges, change],
    })),

  setOverallProgress: (progress) => set({ overallProgress: progress }),
  setCurrentRepo: (repo) => set({ currentRepo: repo }),

  // Reset
  reset: () =>
    set({
      isDialogOpen: false,
      activeOrchestration: null,
      ...initialFormState,
      ...initialExecutionState,
      isCreating: false,
      isStarting: false,
    }),

  resetForm: () => set(initialFormState),
}));
