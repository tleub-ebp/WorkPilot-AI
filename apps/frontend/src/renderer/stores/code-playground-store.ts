import { create } from 'zustand';

/**
 * Result of code playground generation
 */
export interface PlaygroundFile {
  path: string;
  content: string;
  size: number;
}

export interface PlaygroundResult {
  html?: string;
  css?: string;
  javascript?: string;
  files?: PlaygroundFile[];
  integrationNotes?: string;
  playgroundType: string;
  sandboxType: string;
}

export type CodePlaygroundPhase = 'idle' | 'generating' | 'ready' | 'error';

interface CodePlaygroundState {
  // State
  phase: CodePlaygroundPhase;
  status: string;
  streamingOutput: string;
  result: PlaygroundResult | null;
  error: string | null;
  isOpen: boolean;
  initialIdea: string;
  playgroundType: 'html' | 'react' | 'vanilla-js' | 'python' | 'node';
  sandboxType: 'iframe' | 'docker' | 'webworker';

  // Actions
  openDialog: (idea: string, playgroundType?: 'html' | 'react' | 'vanilla-js' | 'python' | 'node', sandboxType?: 'iframe' | 'docker' | 'webworker') => void;
  closeDialog: () => void;
  setPhase: (phase: CodePlaygroundPhase) => void;
  setStatus: (status: string) => void;
  appendStreamingOutput: (chunk: string) => void;
  setResult: (result: PlaygroundResult) => void;
  setError: (error: string) => void;
  setPlaygroundType: (playgroundType: 'html' | 'react' | 'vanilla-js' | 'python' | 'node') => void;
  setSandboxType: (sandboxType: 'iframe' | 'docker' | 'webworker') => void;
  reset: () => void;
}

const initialState = {
  phase: 'idle' as CodePlaygroundPhase,
  status: '',
  streamingOutput: '',
  result: null,
  error: null,
  isOpen: false,
  initialIdea: '',
  playgroundType: 'html' as const,
  sandboxType: 'iframe' as const,
};

export const useCodePlaygroundStore = create<CodePlaygroundState>((set) => ({
  ...initialState,

  openDialog: (idea, playgroundType = 'html', sandboxType = 'iframe') =>
    set({
      isOpen: true,
      initialIdea: idea,
      playgroundType,
      sandboxType,
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
      phase: 'ready',
    }),

  setError: (error) =>
    set({
      error,
      phase: 'error',
    }),

  setPlaygroundType: (playgroundType) => set({ playgroundType }),

  setSandboxType: (sandboxType) => set({ sandboxType }),

  reset: () => set(initialState),
}));

/**
 * Start code playground generation via IPC
 */
export function startPlayground(projectId: string, idea: string, playgroundType: string, sandboxType: string) {
  const store = useCodePlaygroundStore.getState();
  store.reset();
  store.setPhase('generating');
  store.setStatus('Starting playground generation...');
  
  if (window.electronAPI?.startCodePlayground) {
    window.electronAPI.startCodePlayground(projectId, idea, playgroundType, sandboxType);
  }
}

/**
 * Setup IPC listeners for code playground events.
 * Call this once when the app initializes.
 * Returns a cleanup function to unsubscribe all listeners.
 */
export function setupCodePlaygroundListeners() {
  const store = () => useCodePlaygroundStore.getState();

  // Listen for streaming chunks
  const unsubChunk = window.electronAPI.onCodePlaygroundStreamChunk((chunk: string) => {
    store().appendStreamingOutput(chunk);
  });

  // Listen for status updates
  const unsubStatus = window.electronAPI.onCodePlaygroundStatus((status: string) => {
    store().setStatus(status);
  });

  // Listen for errors
  const unsubError = window.electronAPI.onCodePlaygroundError((error: string) => {
    store().setError(error);
  });

  // Listen for completion with structured result
  const unsubComplete = window.electronAPI.onCodePlaygroundComplete(
    (result: PlaygroundResult) => {
      store().setResult(result);
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
export const openCodePlaygroundDialog = () => {
  useCodePlaygroundStore.getState().reset();
  // This would be handled by the component that opens the dialog
};
