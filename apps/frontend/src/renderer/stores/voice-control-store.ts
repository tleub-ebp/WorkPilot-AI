import { create } from 'zustand';

/**
 * Result of voice command processing
 */
export interface VoiceControlResult {
  transcript: string;
  command: string;
  action: string;
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  parameters: Record<string, any>;
  confidence: number;
}

export type VoiceControlPhase = 'idle' | 'recording' | 'processing' | 'complete' | 'error';

interface VoiceControlState {
  // State
  phase: VoiceControlPhase;
  status: string;
  streamingOutput: string;
  result: VoiceControlResult | null;
  error: string | null;
  isOpen: boolean;
  isListening: boolean;
  audioLevel: number;
  duration: number;

  // Actions
  openDialog: () => void;
  closeDialog: () => void;
  setPhase: (phase: VoiceControlPhase) => void;
  setStatus: (status: string) => void;
  appendStreamingOutput: (chunk: string) => void;
  setResult: (result: VoiceControlResult) => void;
  setError: (error: string) => void;
  setListening: (listening: boolean) => void;
  setAudioLevel: (level: number) => void;
  setDuration: (duration: number) => void;
  reset: () => void;
}

const initialState = {
  phase: 'idle' as VoiceControlPhase,
  status: '',
  streamingOutput: '',
  result: null,
  error: null,
  isOpen: false,
  isListening: false,
  audioLevel: 0,
  duration: 0,
};

export const useVoiceControlStore = create<VoiceControlState>((set) => ({
  ...initialState,

  openDialog: () =>
    set({
      isOpen: true,
      phase: 'idle',
      status: '',
      streamingOutput: '',
      result: null,
      error: null,
      isListening: false,
      audioLevel: 0,
      duration: 0,
    }),

  closeDialog: () =>
    set({
      isOpen: false,
      phase: 'idle',
      status: '',
      streamingOutput: '',
      result: null,
      error: null,
      isListening: false,
      audioLevel: 0,
      duration: 0,
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

  setListening: (listening) => set({ isListening: listening }),

  setAudioLevel: (level) => set({ audioLevel: level }),

  setDuration: (duration) => set({ duration }),

  reset: () => set(initialState),
}));

/**
 * Start voice recording via IPC
 */
export function startRecording(): void {
  const store = useVoiceControlStore.getState();

  // Reset recording state
  store.setPhase('recording');
  store.setStatus('Listening...');
  store.appendStreamingOutput(''); // Clear by setting fresh state
  useVoiceControlStore.setState({ 
    streamingOutput: '', 
    error: null, 
    result: null,
    isListening: true,
    audioLevel: 0,
    duration: 0
  });

  // Send recording request via IPC
  window.electronAPI.startVoiceRecording();
}

/**
 * Stop voice recording via IPC
 */
export function stopRecording(): void {
  const store = useVoiceControlStore.getState();
  
  store.setPhase('processing');
  store.setStatus('Processing voice command...');
  store.setListening(false);

  // Send stop request via IPC
  window.electronAPI.stopVoiceRecording();
}

/**
 * Setup IPC listeners for voice control events.
 * Call this once when the app initializes.
 * Returns a cleanup function to unsubscribe all listeners.
 */
export function setupVoiceControlListeners(): () => void {
  const store = () => useVoiceControlStore.getState();

  // Listen for streaming chunks
  const unsubChunk = window.electronAPI.onVoiceControlStreamChunk((chunk: string) => {
    store().appendStreamingOutput(chunk);
  });

  // Listen for status updates
  const unsubStatus = window.electronAPI.onVoiceControlStatus((status: string) => {
    store().setStatus(status);
  });

  // Listen for errors
  const unsubError = window.electronAPI.onVoiceControlError((error: string) => {
    store().setError(error);
  });

  // Listen for completion with structured result
  const unsubComplete = window.electronAPI.onVoiceControlComplete(
    (result: VoiceControlResult) => {
      store().setResult(result);
    }
  );

  // Listen for audio level updates
  const unsubAudioLevel = window.electronAPI.onVoiceControlAudioLevel((level: number) => {
    store().setAudioLevel(level);
  });

  // Listen for duration updates
  const unsubDuration = window.electronAPI.onVoiceControlDuration((duration: number) => {
    store().setDuration(duration);
  });

  return () => {
    unsubChunk();
    unsubStatus();
    unsubError();
    unsubComplete();
    unsubAudioLevel();
    unsubDuration();
  };
}

export const openVoiceControlDialog = () => {
  useVoiceControlStore.getState().reset();
  useVoiceControlStore.getState().openDialog();
};
