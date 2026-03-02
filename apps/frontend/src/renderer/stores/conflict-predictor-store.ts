import { create } from 'zustand';

/**
 * Conflict risk information
 */
export interface ConflictRisk {
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  conflict_type: string;
  file_path: string;
  worktree1: string;
  worktree2: string;
  branch1: string;
  branch2: string;
  description: string;
  resolution_strategy: string;
}

/**
 * File modification information
 */
export interface FileModification {
  file_path: string;
  modification_type: 'added' | 'modified' | 'deleted' | 'renamed';
  lines_added: number;
  lines_removed: number;
  worktree_name: string;
  branch_name: string;
}

/**
 * Result of conflict prediction analysis
 */
export interface ConflictPredictionResult {
  total_worktrees: number;
  active_worktrees: string[];
  conflicts_detected: ConflictRisk[];
  modified_files: FileModification[];
  recommendations: string[];
  safe_merge_order: string[];
  high_risk_areas: string[];
  summary: {
    critical_conflicts: number;
    high_conflicts: number;
    medium_conflicts: number;
    total_conflicts: number;
    risk_assessment: string;
  };
}

export type ConflictPredictorPhase = 'idle' | 'analyzing' | 'complete' | 'error';

interface ConflictPredictorState {
  // State
  phase: ConflictPredictorPhase;
  status: string;
  streamingOutput: string;
  result: ConflictPredictionResult | null;
  error: string | null;
  isOpen: boolean;

  // Actions
  openDialog: () => void;
  closeDialog: () => void;
  setPhase: (phase: ConflictPredictorPhase) => void;
  setStatus: (status: string) => void;
  appendStreamingOutput: (chunk: string) => void;
  setResult: (result: ConflictPredictionResult) => void;
  setError: (error: string) => void;
  reset: () => void;
}

const initialState = {
  phase: 'idle' as ConflictPredictorPhase,
  status: '',
  streamingOutput: '',
  result: null,
  error: null,
  isOpen: false,
};

export const useConflictPredictorStore = create<ConflictPredictorState>((set) => ({
  ...initialState,

  openDialog: () =>
    set({
      isOpen: true,
      phase: 'idle',
      status: '',
      streamingOutput: '',
      result: null,
      error: null,
    }),

  closeDialog: () =>
    set({
      isOpen: false,
      phase: 'idle',
      status: '',
      streamingOutput: '',
      result: null,
      error: null,
    }),

  setPhase: (phase) => set({ phase }),

  setStatus: (status) => set({ status }),

  appendStreamingOutput: (chunk) =>
    set((state) => ({
      streamingOutput: state.streamingOutput + chunk,
    })),

  setResult: (result) =>
    set({
      result,
      phase: 'complete',
    }),

  setError: (error) =>
    set({
      error,
      phase: 'error',
    }),

  reset: () =>
    set({
      phase: 'idle',
      status: '',
      streamingOutput: '',
      result: null,
      error: null,
    }),
}));

/**
 * Start conflict prediction analysis
 */
export const startConflictPrediction = async (projectId: string) => {
  useConflictPredictorStore.setState({
    phase: 'analyzing',
    status: 'Starting conflict analysis...',
    streamingOutput: '',
    result: null,
    error: null,
  });

  try {
    const { conflictPredictorStartAnalysis } = await import('../electron/ipc-handlers');
    await conflictPredictorStartAnalysis(projectId);
  } catch (error) {
    useConflictPredictorStore.setState({
      error: error instanceof Error ? error.message : 'Failed to start conflict analysis',
      phase: 'error',
    });
  }
};

/**
 * Setup IPC event listeners for conflict predictor events
 */
export const setupConflictPredictorListeners = () => {
  const cleanup: (() => void)[] = [];

  // Listen for conflict predictor events
  const setupEventListener = async () => {
    const { ipcRenderer } = await import('electron');

    const handleConflictPredictorEvent = (_event: any, data: any) => {
      const { type, data: eventData } = data;

      switch (type) {
        case 'start':
          useConflictPredictorStore.setState({
            phase: 'analyzing',
            status: eventData.status || 'Starting analysis...',
          });
          break;

        case 'progress':
          useConflictPredictorStore.setState((state) => ({
            status: eventData.status || 'Analyzing...',
            streamingOutput: state.streamingOutput + `${eventData.status}\n`,
          }));
          break;

        case 'complete':
          useConflictPredictorStore.setState({
            phase: 'complete',
            status: 'Analysis complete',
            result: eventData,
          });
          break;

        case 'error':
          useConflictPredictorStore.setState({
            phase: 'error',
            error: eventData.error || 'Analysis failed',
          });
          break;
      }
    };

    const handleConflictPredictorResult = (_event: any, data: any) => {
      useConflictPredictorStore.setState({
        result: data,
        phase: 'complete',
      });
    };

    const handleConflictPredictorError = (_event: any, error: string) => {
      useConflictPredictorStore.setState({
        error,
        phase: 'error',
      });
    };

    // Register event listeners
    ipcRenderer.on('conflict-predictor-event', handleConflictPredictorEvent);
    ipcRenderer.on('conflict-predictor-result', handleConflictPredictorResult);
    ipcRenderer.on('conflict-predictor-error', handleConflictPredictorError);

    // Store cleanup functions
    cleanup.push(() => {
      ipcRenderer.removeListener('conflict-predictor-event', handleConflictPredictorEvent);
      ipcRenderer.removeListener('conflict-predictor-result', handleConflictPredictorResult);
      ipcRenderer.removeListener('conflict-predictor-error', handleConflictPredictorError);
    });
  };

  setupEventListener();

  // Return cleanup function
  return () => {
    cleanup.forEach(fn => fn());
  };
};
