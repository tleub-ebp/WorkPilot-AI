import { contextBridge, ipcRenderer } from 'electron';
import type { ContextAwareSnippetResult } from '../../../main/context-aware-snippets-service';

/**
 * Context-Aware Snippets API
 * 
 * Provides access to context-aware snippet generation functionality
 * from the renderer process.
 */

// Generate a context-aware snippet
export const generateContextAwareSnippet = async (
  projectDir: string,
  snippetType: 'component' | 'function' | 'class' | 'hook' | 'utility' | 'api' | 'test',
  description: string,
  language?: string,
  model?: string,
  thinkingLevel?: string
): Promise<{ success: boolean; error?: string }> => {
  return await ipcRenderer.invoke('context-aware-snippets:generate', {
    projectDir,
    snippetType,
    description,
    language,
    model,
    thinkingLevel,
  });
};

// Cancel active snippet generation
export const cancelSnippetGeneration = async (): Promise<{ success: boolean; cancelled?: boolean; error?: string }> => {
  return await ipcRenderer.invoke('context-aware-snippets:cancel');
};

// Configure the snippets service
export const configureSnippetsService = async (
  pythonPath?: string,
  autoBuildSourcePath?: string
): Promise<{ success: boolean; error?: string }> => {
  return await ipcRenderer.invoke('context-aware-snippets:configure', {
    pythonPath,
    autoBuildSourcePath,
  });
};

// Event listeners for streaming updates
export const onSnippetStreamChunk = (callback: (chunk: string) => void) => {
  ipcRenderer.on('context-aware-snippets:stream-chunk', (_, chunk) => callback(chunk));
};

export const onSnippetStatus = (callback: (status: string) => void) => {
  ipcRenderer.on('context-aware-snippets:status', (_, status) => callback(status));
};

export const onSnippetError = (callback: (error: string) => void) => {
  ipcRenderer.on('context-aware-snippets:error', (_, error) => callback(error));
};

export const onSnippetComplete = (callback: (result: ContextAwareSnippetResult) => void) => {
  ipcRenderer.on('context-aware-snippets:complete', (_, result) => callback(result));
};

// Cleanup event listeners
export const removeSnippetStreamChunkListener = (callback: (chunk: string) => void) => {
  ipcRenderer.removeListener('context-aware-snippets:stream-chunk', callback);
};

export const removeSnippetStatusListener = (callback: (status: string) => void) => {
  ipcRenderer.removeListener('context-aware-snippets:status', callback);
};

export const removeSnippetErrorListener = (callback: (error: string) => void) => {
  ipcRenderer.removeListener('context-aware-snippets:error', callback);
};

export const removeSnippetCompleteListener = (callback: (result: ContextAwareSnippetResult) => void) => {
  ipcRenderer.removeListener('context-aware-snippets:complete', callback);
};

// Expose the API to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  ...window.electronAPI,
  // Context-Aware Snippets methods
  generateContextAwareSnippet,
  cancelSnippetGeneration,
  configureSnippetsService,
  // Event listeners
  onSnippetStreamChunk,
  onSnippetStatus,
  onSnippetError,
  onSnippetComplete,
  removeSnippetStreamChunkListener,
  removeSnippetStatusListener,
  removeSnippetErrorListener,
  removeSnippetCompleteListener,
});

// Type declarations for the exposed API
declare global {
  interface Window {
    electronAPI: {
      // Existing methods...
      generateContextAwareSnippet: typeof generateContextAwareSnippet;
      cancelSnippetGeneration: typeof cancelSnippetGeneration;
      configureSnippetsService: typeof configureSnippetsService;
      onSnippetStreamChunk: typeof onSnippetStreamChunk;
      onSnippetStatus: typeof onSnippetStatus;
      onSnippetError: typeof onSnippetError;
      onSnippetComplete: typeof onSnippetComplete;
      removeSnippetStreamChunkListener: typeof removeSnippetStreamChunkListener;
      removeSnippetStatusListener: typeof removeSnippetStatusListener;
      removeSnippetErrorListener: typeof removeSnippetErrorListener;
      removeSnippetCompleteListener: typeof removeSnippetCompleteListener;
      // Add other existing methods as needed
      [key: string]: any;
    };
  }
}
