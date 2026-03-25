import { create } from 'zustand';
import type {
  LearningPattern,
  LearningSummary,
  LearningLoopCompleteResult,
} from '../../shared/types/learning-loop';

export type LearningLoopPhase = 'idle' | 'analyzing' | 'complete' | 'error';

interface LearningLoopState {
  // State
  phase: LearningLoopPhase;
  status: string;
  streamingOutput: string;
  patterns: LearningPattern[];
  summary: LearningSummary | null;
  error: string | null;
  isOpen: boolean;
  isLoading: boolean;

  // Actions
  openDialog: () => void;
  closeDialog: () => void;
  setPhase: (phase: LearningLoopPhase) => void;
  setStatus: (status: string) => void;
  appendStreamingOutput: (chunk: string) => void;
  setPatterns: (patterns: LearningPattern[]) => void;
  setSummary: (summary: LearningSummary | null) => void;
  setError: (error: string) => void;
  setIsLoading: (isLoading: boolean) => void;
  updatePatternInList: (patternId: string, updates: Partial<LearningPattern>) => void;
  removePatternFromList: (patternId: string) => void;
  reset: () => void;
}

const initialState = {
  phase: 'idle' as LearningLoopPhase,
  status: '',
  streamingOutput: '',
  patterns: [] as LearningPattern[],
  summary: null as LearningSummary | null,
  error: null as string | null,
  isOpen: false,
  isLoading: false,
};

export const useLearningLoopStore = create<LearningLoopState>((set) => ({
  ...initialState,

  openDialog: () =>
    set({
      isOpen: true,
      phase: 'idle',
      status: '',
      streamingOutput: '',
      error: null,
    }),

  closeDialog: () =>
    set({
      isOpen: false,
      phase: 'idle',
      status: '',
      streamingOutput: '',
      error: null,
    }),

  setPhase: (phase) => set({ phase }),

  setStatus: (status) => set({ status }),

  appendStreamingOutput: (chunk) =>
    set((state) => ({
      streamingOutput: state.streamingOutput + chunk,
    })),

  setPatterns: (patterns) => set({ patterns }),

  setSummary: (summary) => set({ summary }),

  setError: (error) =>
    set({
      error,
      phase: 'error',
    }),

  setIsLoading: (isLoading) => set({ isLoading }),

  updatePatternInList: (patternId, updates) =>
    set((state) => ({
      patterns: state.patterns.map((p) =>
        p.pattern_id === patternId ? { ...p, ...updates } : p
      ),
    })),

  removePatternFromList: (patternId) =>
    set((state) => ({
      patterns: state.patterns.filter((p) => p.pattern_id !== patternId),
      summary: state.summary
        ? { ...state.summary, total_patterns: state.summary.total_patterns - 1 }
        : null,
    })),

  reset: () => set(initialState),
}));

/**
 * Load patterns from the backend for a project
 */
export async function loadLearningPatterns(projectDir: string): Promise<void> {
  const store = useLearningLoopStore.getState();
  store.setIsLoading(true);
  try {
    const result = await globalThis.electronAPI.getLearningPatterns(projectDir);
    if (result.success && result.data) {
      store.setPatterns(result.data);
    } else if (result.error) {
      console.error('[LearningLoop] Failed to load patterns:', result.error);
    }
  } catch (error) {
    console.error('[LearningLoop] Error loading patterns:', error);
  } finally {
    store.setIsLoading(false);
  }
}

/**
 * Load summary from the backend for a project
 */
export async function loadLearningSummary(projectDir: string): Promise<void> {
  try {
    const result = await globalThis.electronAPI.getLearningSummary(projectDir);
    if (result.success && result.data) {
      useLearningLoopStore.getState().setSummary(result.data);
    }
  } catch (error) {
    console.error('[LearningLoop] Error loading summary:', error);
  }
}

/**
 * Start learning loop analysis via IPC
 */
export function startLearningAnalysis(projectDir: string, specId?: string): void {
  const store = useLearningLoopStore.getState();
  store.setPhase('analyzing');
  store.setStatus('');
  useLearningLoopStore.setState({ streamingOutput: '', error: null });

  globalThis.electronAPI.runLearningAnalysis(projectDir, specId);
}

/**
 * Cancel learning loop analysis via IPC
 */
export async function cancelLearningAnalysis(): Promise<void> {
  await globalThis.electronAPI.stopLearningAnalysis();
  useLearningLoopStore.getState().setPhase('idle');
}

/**
 * Delete a pattern
 */
export async function deleteLearningPattern(projectDir: string, patternId: string): Promise<boolean> {
  try {
    const result = await globalThis.electronAPI.deleteLearningPattern(projectDir, patternId);
    if (result.success) {
      useLearningLoopStore.getState().removePatternFromList(patternId);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Toggle a pattern's enabled state
 */
export async function toggleLearningPattern(projectDir: string, patternId: string): Promise<boolean> {
  try {
    const result = await globalThis.electronAPI.toggleLearningPattern(projectDir, patternId);
    if (result.success && result.data !== undefined) {
      useLearningLoopStore.getState().updatePatternInList(patternId, { enabled: result.data });
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Setup IPC listeners for learning loop events.
 * Call this once when the app initializes.
 * Returns a cleanup function to unsubscribe all listeners.
 */
export function setupLearningLoopListeners(): () => void {
  const store = () => useLearningLoopStore.getState();
  const noop = () => { /* noop */ };

  // Guard: API methods may not exist in browser-mock / dev mode
  const api = globalThis.electronAPI;
  if (!api?.onLearningLoopStreamChunk) {
    return noop;
  }

  // Listen for streaming chunks
  const unsubChunk = api.onLearningLoopStreamChunk((chunk: string) => {
    store().appendStreamingOutput(chunk);
  });

  // Listen for status updates
  const unsubStatus = api.onLearningLoopStatus((status: string) => {
    store().setStatus(status);
  });

  // Listen for errors
  const unsubError = api.onLearningLoopError((error: string) => {
    store().setError(error);
  });

  // Listen for analysis completion
  const unsubComplete = api.onLearningLoopComplete(
    (result: LearningLoopCompleteResult) => {
      store().setPhase('complete');
      if (result.patterns) {
        store().setPatterns(result.patterns);
      }
      if (result.summary) {
        store().setSummary(result.summary);
      }
      store().setStatus('Analysis complete');
    }
  );

  return () => {
    unsubChunk();
    unsubStatus();
    unsubError();
    unsubComplete();
  };
}

// Helper function to open dialog
export const openLearningLoopDialog = () => {
  useLearningLoopStore.getState().reset();
  useLearningLoopStore.getState().openDialog();
};
