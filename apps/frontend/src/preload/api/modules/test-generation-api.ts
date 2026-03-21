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
    ipcRenderer.on('test-generation:status', (_event: IpcRendererEvent, status: string) => callback(status));
  },

  onTestGenerationError: (callback: (error: string) => void) => {
    ipcRenderer.on('test-generation:error', (_event: IpcRendererEvent, error: string) => callback(error));
  },

  onTestGenerationResult: (callback: (result: any) => void) => {
    ipcRenderer.on('test-generation:result', (_event: IpcRendererEvent, result: any) => callback(result));
  },

  onTestGenerationComplete: (callback: (result: any) => void) => {
    ipcRenderer.on('test-generation:complete', (_event: IpcRendererEvent, result: any) => callback(result));
  },

  removeTestGenerationStatusListener: (callback: (status: string) => void) => {
    ipcRenderer.removeListener('test-generation:status', (_event: IpcRendererEvent, status: string) => callback(status));
  },

  removeTestGenerationErrorListener: (callback: (error: string) => void) => {
    ipcRenderer.removeListener('test-generation:error', (_event: IpcRendererEvent, error: string) => callback(error));
  },

  removeTestGenerationResultListener: (callback: (result: any) => void) => {
    ipcRenderer.removeListener('test-generation:result', (_event: IpcRendererEvent, result: any) => callback(result));
  },

  removeTestGenerationCompleteListener: (callback: (result: any) => void) => {
    ipcRenderer.removeListener('test-generation:complete', (_event: IpcRendererEvent, result: any) => callback(result));
  },
});
