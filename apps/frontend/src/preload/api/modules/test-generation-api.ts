import { ipcRenderer, IpcRendererEvent } from 'electron';

/**
 * Test Generation API
 *
 * Provides access to test generation functionality from the renderer process.
 */

export interface TestGenerationAPI {
  analyzeTestCoverage: (filePath: string, existingTestPath?: string, projectPath?: string) => Promise<{ success: boolean; error?: string }>;
  generateUnitTests: (filePath: string, existingTestPath?: string, coverageTarget?: number, projectPath?: string) => Promise<{ success: boolean; error?: string }>;
  generateE2ETests: (userStory: string, targetModule: string, projectPath?: string) => Promise<{ success: boolean; error?: string }>;
  generateTDDTests: (description: string, language: string, snippetType: string, projectPath?: string) => Promise<{ success: boolean; error?: string }>;
  cancelTestGeneration: () => Promise<{ success: boolean; cancelled?: boolean; error?: string }>;
  onTestGenerationStatus: (callback: (status: string) => void) => void;
  onTestGenerationError: (callback: (error: string) => void) => void;
  onTestGenerationResult: (callback: (result: any) => void) => void;
  onTestGenerationComplete: (callback: (result: any) => void) => void;
  removeTestGenerationStatusListener: (callback: (status: string) => void) => void;
  removeTestGenerationErrorListener: (callback: (error: string) => void) => void;
  removeTestGenerationResultListener: (callback: (result: any) => void) => void;
  removeTestGenerationCompleteListener: (callback: (result: any) => void) => void;
}

// Maps to store callback → actual IPC listener so removeListener can find the exact reference
const statusListeners = new Map<Function, (event: IpcRendererEvent, status: string) => void>();
const errorListeners = new Map<Function, (event: IpcRendererEvent, error: string) => void>();
const resultListeners = new Map<Function, (event: IpcRendererEvent, result: any) => void>();
const completeListeners = new Map<Function, (event: IpcRendererEvent, result: any) => void>();

export const createTestGenerationAPI = (): TestGenerationAPI => ({
  analyzeTestCoverage: async (
    filePath: string,
    existingTestPath?: string,
    projectPath?: string
  ): Promise<{ success: boolean; error?: string }> => {
    return await ipcRenderer.invoke('test-generation:analyze-coverage', {
      filePath,
      existingTestPath,
      projectPath,
    });
  },

  generateUnitTests: async (
    filePath: string,
    existingTestPath?: string,
    coverageTarget?: number,
    projectPath?: string
  ): Promise<{ success: boolean; error?: string }> => {
    return await ipcRenderer.invoke('test-generation:generate-unit', {
      filePath,
      existingTestPath,
      coverageTarget,
      projectPath,
    });
  },

  generateE2ETests: async (
    userStory: string,
    targetModule: string,
    projectPath?: string
  ): Promise<{ success: boolean; error?: string }> => {
    return await ipcRenderer.invoke('test-generation:generate-e2e', {
      userStory,
      targetModule,
      projectPath,
    });
  },

  generateTDDTests: async (
    description: string,
    language: string,
    snippetType: string,
    projectPath?: string
  ): Promise<{ success: boolean; error?: string }> => {
    return await ipcRenderer.invoke('test-generation:generate-tdd', {
      description,
      language,
      snippetType,
      projectPath,
    });
  },

  cancelTestGeneration: async (): Promise<{ success: boolean; cancelled?: boolean; error?: string }> => {
    return await ipcRenderer.invoke('test-generation:cancel');
  },

  onTestGenerationStatus: (callback: (status: string) => void) => {
    // Remove any existing listener for this callback before adding a new one
    const existing = statusListeners.get(callback);
    if (existing) {
      ipcRenderer.removeListener('test-generation:status', existing);
    }
    const listener = (_event: IpcRendererEvent, status: string) => callback(status);
    statusListeners.set(callback, listener);
    ipcRenderer.on('test-generation:status', listener);
  },

  onTestGenerationError: (callback: (error: string) => void) => {
    const existing = errorListeners.get(callback);
    if (existing) {
      ipcRenderer.removeListener('test-generation:error', existing);
    }
    const listener = (_event: IpcRendererEvent, error: string) => callback(error);
    errorListeners.set(callback, listener);
    ipcRenderer.on('test-generation:error', listener);
  },

  onTestGenerationResult: (callback: (result: any) => void) => {
    const existing = resultListeners.get(callback);
    if (existing) {
      ipcRenderer.removeListener('test-generation:result', existing);
    }
    const listener = (_event: IpcRendererEvent, result: any) => callback(result);
    resultListeners.set(callback, listener);
    ipcRenderer.on('test-generation:result', listener);
  },

  onTestGenerationComplete: (callback: (result: any) => void) => {
    const existing = completeListeners.get(callback);
    if (existing) {
      ipcRenderer.removeListener('test-generation:complete', existing);
    }
    const listener = (_event: IpcRendererEvent, result: any) => callback(result);
    completeListeners.set(callback, listener);
    ipcRenderer.on('test-generation:complete', listener);
  },

  removeTestGenerationStatusListener: (callback: (status: string) => void) => {
    const listener = statusListeners.get(callback);
    if (listener) {
      ipcRenderer.removeListener('test-generation:status', listener);
      statusListeners.delete(callback);
    }
  },

  removeTestGenerationErrorListener: (callback: (error: string) => void) => {
    const listener = errorListeners.get(callback);
    if (listener) {
      ipcRenderer.removeListener('test-generation:error', listener);
      errorListeners.delete(callback);
    }
  },

  removeTestGenerationResultListener: (callback: (result: any) => void) => {
    const listener = resultListeners.get(callback);
    if (listener) {
      ipcRenderer.removeListener('test-generation:result', listener);
      resultListeners.delete(callback);
    }
  },

  removeTestGenerationCompleteListener: (callback: (result: any) => void) => {
    const listener = completeListeners.get(callback);
    if (listener) {
      ipcRenderer.removeListener('test-generation:complete', listener);
      completeListeners.delete(callback);
    }
  },
});
