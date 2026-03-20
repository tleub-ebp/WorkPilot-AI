import { create } from 'zustand';
import type { AppEmulatorConfig } from '../../main/app-emulator-service';

export type AppEmulatorPhase = 'idle' | 'detecting' | 'starting' | 'running' | 'stopped' | 'error';

interface AppEmulatorState {
  isOpen: boolean;
  phase: AppEmulatorPhase;
  config: AppEmulatorConfig | null;
  url: string | null;
  output: string;
  error: string | null;
  status: string;
  taskId: string | null;

  // Actions
  openDialog: (taskId?: string) => void;
  closeDialog: () => void;
  setPhase: (phase: AppEmulatorPhase) => void;
  setConfig: (config: AppEmulatorConfig) => void;
  setUrl: (url: string) => void;
  appendOutput: (line: string) => void;
  setError: (error: string) => void;
  setStatus: (status: string) => void;
  reset: () => void;
}

const initialState = {
  isOpen: false,
  phase: 'idle' as AppEmulatorPhase,
  config: null as AppEmulatorConfig | null,
  url: null as string | null,
  output: '',
  error: null as string | null,
  status: '',
  taskId: null as string | null,
};

export const useAppEmulatorStore = create<AppEmulatorState>((set) => ({
  ...initialState,

  openDialog: (taskId?: string) =>
    set((state) => {
      // If already in progress or running, just show the dialog without resetting state
      if (state.phase === 'detecting' || state.phase === 'starting' || state.phase === 'running') {
        return { isOpen: true };
      }
      return {
        isOpen: true,
        phase: 'idle',
        config: null,
        url: null,
        output: '',
        error: null,
        status: '',
        taskId: taskId ?? null,
      };
    }),

  closeDialog: () => {
    // Stop server when closing
    try {
      (globalThis as any).electronAPI?.stopAppEmulator();
    } catch {
      // Ignore errors during cleanup
    }
    set({ ...initialState });
  },

  setPhase: (phase) => set({ phase }),
  setConfig: (config) => set({ config }),
  setUrl: (url) => set({ url }),
  appendOutput: (line) =>
    set((state) => ({
      output: (state.output + line + '\n').slice(-50000),
    })),
  setError: (error) => set({ error, phase: 'error' }),
  setStatus: (status) => set({ status }),
  reset: () => set({ ...initialState }),
}));

/**
 * Start the App Emulator: detect project, then launch server.
 */
export async function startAppEmulator(projectDir: string): Promise<void> {
  const store = useAppEmulatorStore.getState();

  // Guard against concurrent starts — only one detection/start at a time
  const currentPhase = store.phase;
  if (currentPhase === 'detecting' || currentPhase === 'starting' || currentPhase === 'running') {
    return;
  }

  store.setPhase('detecting');
  store.setStatus('Detecting project type...');

  try {
    const result = await (globalThis as any).electronAPI.detectAppProject(projectDir);

    if (!result.success) {
      store.setError(result.error || 'Detection failed');
      return;
    }

    const config = result.data;
    store.setConfig(config);
    store.setPhase('starting');
    store.setStatus(`Starting: ${config.startCommand}`);

    const startResult = await (globalThis as any).electronAPI.startAppEmulator(config);
    if (!startResult.success) {
      // "Already starting" means a concurrent call is in progress — silently ignore,
      // the real start will emit events (onReady / onError / onStopped) directly.
      if (startResult.error !== 'Already starting — ignoring duplicate request') {
        store.setError(startResult.error || 'Failed to start server');
      }
    }
  } catch (err: any) {
    store.setError(err.message || 'An unexpected error occurred');
  }
}

/**
 * Stop the App Emulator server.
 */
export async function stopAppEmulator(): Promise<void> {
  try {
    await (globalThis as any).electronAPI.stopAppEmulator();
  } catch {
    // Ignore
  }
  useAppEmulatorStore.getState().setPhase('stopped');
}

/**
 * Setup IPC listeners. Returns cleanup function.
 */
// Ref-counted singleton: multiple components (ApiExplorer, AppEmulatorDialog) can call
// setupAppEmulatorListeners() safely — IPC listeners are registered only once.
let _listenerRefCount = 0;
let _listenerCleanup: (() => void) | null = null;

export function setupAppEmulatorListeners(): () => void {
  _listenerRefCount++;

  if (_listenerRefCount === 1) {
    // First caller — register the actual IPC listeners
    const store = () => useAppEmulatorStore.getState();

    const unsubStatus = (globalThis as any).electronAPI.onAppEmulatorStatus((status: string) => {
      store().setStatus(status);
    });
    const unsubReady = (globalThis as any).electronAPI.onAppEmulatorReady((url: string) => {
      store().setUrl(url);
      store().setPhase('running');
      store().setStatus(`Running at ${url}`);
    });
    const unsubOutput = (globalThis as any).electronAPI.onAppEmulatorOutput((line: string) => {
      store().appendOutput(line);
    });
    const unsubError = (globalThis as any).electronAPI.onAppEmulatorError((error: string) => {
      store().setError(error);
    });
    const unsubStopped = (globalThis as any).electronAPI.onAppEmulatorStopped(() => {
      const currentPhase = store().phase;
      // Ignore stale stop events from the previous run during a retry (detecting/starting)
      if (currentPhase !== 'error' && currentPhase !== 'detecting' && currentPhase !== 'starting') {
        store().setPhase('stopped');
        store().setStatus('Server stopped');
      }
    });
    const unsubConfig = (globalThis as any).electronAPI.onAppEmulatorConfig((config: AppEmulatorConfig) => {
      store().setConfig(config);
    });

    _listenerCleanup = () => {
      unsubStatus();
      unsubReady();
      unsubOutput();
      unsubError();
      unsubStopped();
      unsubConfig();
    };
  }

  // Each caller gets a cleanup that decrements the ref-count and only truly
  // unregisters when the last subscriber unmounts.
  return () => {
    _listenerRefCount--;
    if (_listenerRefCount === 0 && _listenerCleanup) {
      _listenerCleanup();
      _listenerCleanup = null;
    }
  };
}

/**
 * Open the App Emulator dialog.
 */
export function openAppEmulatorDialog(taskId?: string): void {
  useAppEmulatorStore.getState().openDialog(taskId);
}
