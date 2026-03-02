import { create } from 'zustand';
import type { AppSettings } from '../../shared/types';

/**
 * Natural Language Git store state
 */
export interface NaturalLanguageGitState {
  // UI state
  isOpen: boolean;
  phase: 'idle' | 'processing' | 'complete' | 'error';
  status: string;
  error: string | null;

  // Input/output
  naturalLanguageCommand: string;
  streamingOutput: string;
  result: {
    generatedCommand: string;
    explanation: string;
    executionOutput: string;
    success: boolean;
  } | null;

  // Actions
  openDialog: (initialCommand?: string) => void;
  closeDialog: () => void;
  setNaturalLanguageCommand: (command: string) => void;
  setPhase: (phase: 'idle' | 'processing' | 'complete' | 'error') => void;
  setStatus: (status: string) => void;
  appendStreamingOutput: (chunk: string) => void;
  setResult: (result: {
    generatedCommand: string;
    explanation: string;
    executionOutput: string;
    success: boolean;
  }) => void;
  setError: (error: string) => void;
  reset: () => void;
}

/**
 * Zustand store for Natural Language Git functionality
 */
export const useNaturalLanguageGitStore = create<NaturalLanguageGitState>((set) => ({
  // Initial state
  isOpen: false,
  phase: 'idle',
  status: '',
  error: null,
  naturalLanguageCommand: '',
  streamingOutput: '',
  result: null,

  // Actions
  openDialog: (initialCommand = '') => {
    set({
      isOpen: true,
      phase: 'idle',
      naturalLanguageCommand: initialCommand,
      streamingOutput: '',
      result: null,
      error: null,
      status: '',
    });
  },

  closeDialog: () => {
    set({ isOpen: false });
  },

  setNaturalLanguageCommand: (command: string) => {
    set({ naturalLanguageCommand: command });
  },

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
      status: result.success ? 'Command executed successfully' : 'Command execution failed',
    }),
  setError: (error) =>
    set({
      error,
      phase: 'error',
      status: 'Error',
    }),

  reset: () => set({
    phase: 'idle',
    status: '',
    streamingOutput: '',
    result: null,
    error: null,
  }),
}));

// IPC event handlers
let setupComplete = false;

export function setupNaturalLanguageGitListeners() {
  if (setupComplete) {
    return () => {};
  }

  const store = () => useNaturalLanguageGitStore.getState();

  const handleStatus = (_event: unknown, status: string) => {
    store().setStatus?.(status);
  };

  const handleStreamChunk = (_event: unknown, chunk: string) => {
    store().appendStreamingOutput?.(chunk);
  };

  const handleError = (_event: unknown, error: string) => {
    store().setError?.(error);
  };

  const handleComplete = (_event: unknown, result: {
    generatedCommand: string;
    explanation: string;
    executionOutput: string;
    success: boolean;
  }) => {
    store().setResult?.(result);
  };

  // Register IPC listeners
  if (window.electronAPI?.onNaturalLanguageGitStatus) {
    window.electronAPI.onNaturalLanguageGitStatus(handleStatus);
  }
  if (window.electronAPI?.onNaturalLanguageGitStreamChunk) {
    window.electronAPI.onNaturalLanguageGitStreamChunk(handleStreamChunk);
  }
  if (window.electronAPI?.onNaturalLanguageGitError) {
    window.electronAPI.onNaturalLanguageGitError(handleError);
  }
  if (window.electronAPI?.onNaturalLanguageGitComplete) {
    window.electronAPI.onNaturalLanguageGitComplete(handleComplete);
  }

  setupComplete = true;

  // Cleanup function
  return () => {
    if (window.electronAPI?.removeNaturalLanguageGitStatusListener) {
      window.electronAPI.removeNaturalLanguageGitStatusListener(handleStatus);
    }
    if (window.electronAPI?.removeNaturalLanguageGitStreamChunkListener) {
      window.electronAPI.removeNaturalLanguageGitStreamChunkListener(handleStreamChunk);
    }
    if (window.electronAPI?.removeNaturalLanguageGitErrorListener) {
      window.electronAPI.removeNaturalLanguageGitErrorListener(handleError);
    }
    if (window.electronAPI?.removeNaturalLanguageGitCompleteListener) {
      window.electronAPI.removeNaturalLanguageGitCompleteListener(handleComplete);
    }
    setupComplete = false;
  };
}

/**
 * Start natural language git command processing
 */
export async function executeGitCommand(projectId: string) {
  const store = useNaturalLanguageGitStore.getState();
  const { naturalLanguageCommand } = store;
  
  if (!naturalLanguageCommand.trim()) {
    return;
  }

  // Reset and set processing state
  store.setPhase('processing');
  store.setStatus('Processing command...');
  store.appendStreamingOutput(''); // Clear by setting fresh state
  useNaturalLanguageGitStore.setState({ streamingOutput: '', error: null, result: null });

  try {
    // Get project path
    const projectPath = await window.electronAPI?.getProjectPath(projectId);
    if (!projectPath) {
      throw new Error('Project path not found');
    }

    // Get settings for model configuration
    const settings = await window.electronAPI?.getSettings();
    
    // Call the main process to execute the command
    await window.electronAPI?.executeNaturalLanguageGit({
      projectPath,
      command: naturalLanguageCommand,
      model: settings?.data?.featureModels?.['natural-language-git'],
      thinkingLevel: settings?.data?.featureThinking?.['natural-language-git'],
    });
  } catch (error) {
    store.setError(error instanceof Error ? error.message : 'Unknown error');
  }
}
