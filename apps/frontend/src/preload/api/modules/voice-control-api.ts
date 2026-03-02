/**
 * Voice Control API module for preload script
 * 
 * Provides voice control functionality through IPC communication
 */

export interface VoiceControlAPI {
  // Voice recording control
  startVoiceRecording: (request?: {
    projectDir?: string;
    language?: string;
    model?: string;
    thinkingLevel?: string;
  }) => Promise<{ success: boolean; error?: string }>;
  
  stopVoiceRecording: () => Promise<{ success: boolean; error?: string }>;
  cancelVoiceControl: () => Promise<{ success: boolean; cancelled: boolean; error?: string }>;
  isVoiceControlActive: () => Promise<{ success: boolean; isActive: boolean; error?: string }>;
  
  // Configuration
  configureVoiceControl: (config: {
    pythonPath?: string;
    autoBuildSourcePath?: string;
  }) => Promise<{ success: boolean; error?: string }>;
  
  // Event listeners
  onVoiceControlStatus: (callback: (status: string) => void) => () => void;
  onVoiceControlStreamChunk: (callback: (chunk: string) => void) => () => void;
  onVoiceControlError: (callback: (error: string) => void) => () => void;
  onVoiceControlComplete: (callback: (result: {
    transcript: string;
    command: string;
    action: string;
    parameters: Record<string, any>;
    confidence: number;
  }) => void) => () => void;
  onVoiceControlAudioLevel: (callback: (level: number) => void) => () => void;
  onVoiceControlDuration: (callback: (duration: number) => void) => () => void;
}

export function createVoiceControlAPI(): VoiceControlAPI {
  return {
    // Voice recording control
    startVoiceRecording: async (request) => {
      return await window.electron.invoke('start-voice-recording', request);
    },
    
    stopVoiceRecording: async () => {
      return await window.electron.invoke('stop-voice-recording');
    },
    
    cancelVoiceControl: async () => {
      return await window.electron.invoke('cancel-voice-control');
    },
    
    isVoiceControlActive: async () => {
      return await window.electron.invoke('is-voice-control-active');
    },
    
    // Configuration
    configureVoiceControl: async (config) => {
      return await window.electron.invoke('configure-voice-control', config);
    },
    
    // Event listeners
    onVoiceControlStatus: (callback) => {
      const unsubscribe = window.electron.onVoiceControlStatus(callback);
      return unsubscribe;
    },
    
    onVoiceControlStreamChunk: (callback) => {
      const unsubscribe = window.electron.onVoiceControlStreamChunk(callback);
      return unsubscribe;
    },
    
    onVoiceControlError: (callback) => {
      const unsubscribe = window.electron.onVoiceControlError(callback);
      return unsubscribe;
    },
    
    onVoiceControlComplete: (callback) => {
      const unsubscribe = window.electron.onVoiceControlComplete(callback);
      return unsubscribe;
    },
    
    onVoiceControlAudioLevel: (callback) => {
      const unsubscribe = window.electron.onVoiceControlAudioLevel(callback);
      return unsubscribe;
    },
    
    onVoiceControlDuration: (callback) => {
      const unsubscribe = window.electron.onVoiceControlDuration(callback);
      return unsubscribe;
    },
  };
}
