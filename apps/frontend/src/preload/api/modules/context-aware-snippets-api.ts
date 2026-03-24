import { ipcRenderer, IpcRendererEvent } from 'electron';
import type { ContextAwareSnippetResult } from '../../../main/context-aware-snippets-service';

/**
 * Context-Aware Snippets API
 * 
 * Provides access to context-aware snippet generation functionality
 * from the renderer process.
 */

export interface ContextAwareSnippetsAPI {
  generateContextAwareSnippet: (
    projectDir: string,
    snippetType: 'component' | 'function' | 'class' | 'hook' | 'utility' | 'api' | 'test',
    description: string,
    language?: string,
    model?: string,
    thinkingLevel?: string
  ) => Promise<{ success: boolean; error?: string }>;
  cancelSnippetGeneration: () => Promise<{ success: boolean; cancelled?: boolean; error?: string }>;
  configureSnippetsService: (
    pythonPath?: string,
    autoBuildSourcePath?: string
  ) => Promise<{ success: boolean; error?: string }>;
  onSnippetStreamChunk: (callback: (chunk: string) => void) => void;
  onSnippetStatus: (callback: (status: string) => void) => void;
  onSnippetError: (callback: (error: string) => void) => void;
  onSnippetComplete: (callback: (result: ContextAwareSnippetResult) => void) => void;
  removeSnippetStreamChunkListener: (callback: (chunk: string) => void) => void;
  removeSnippetStatusListener: (callback: (status: string) => void) => void;
  removeSnippetErrorListener: (callback: (error: string) => void) => void;
  removeSnippetCompleteListener: (callback: (result: ContextAwareSnippetResult) => void) => void;
}

export const createContextAwareSnippetsAPI = (): ContextAwareSnippetsAPI => ({
  generateContextAwareSnippet: async (
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
  },

  cancelSnippetGeneration: async (): Promise<{ success: boolean; cancelled?: boolean; error?: string }> => {
    return await ipcRenderer.invoke('context-aware-snippets:cancel');
  },

  configureSnippetsService: async (
    pythonPath?: string,
    autoBuildSourcePath?: string
  ): Promise<{ success: boolean; error?: string }> => {
    return await ipcRenderer.invoke('context-aware-snippets:configure', {
      pythonPath,
      autoBuildSourcePath,
    });
  },

  onSnippetStreamChunk: (callback: (chunk: string) => void) => {
    ipcRenderer.on('context-aware-snippets:stream-chunk', (_event: IpcRendererEvent, chunk: string) => callback(chunk));
  },

  onSnippetStatus: (callback: (status: string) => void) => {
    ipcRenderer.on('context-aware-snippets:status', (_event: IpcRendererEvent, status: string) => callback(status));
  },

  onSnippetError: (callback: (error: string) => void) => {
    ipcRenderer.on('context-aware-snippets:error', (_event: IpcRendererEvent, error: string) => callback(error));
  },

  onSnippetComplete: (callback: (result: ContextAwareSnippetResult) => void) => {
    ipcRenderer.on('context-aware-snippets:complete', (_event: IpcRendererEvent, result: ContextAwareSnippetResult) => callback(result));
  },

  removeSnippetStreamChunkListener: (callback: (chunk: string) => void) => {
    ipcRenderer.removeListener('context-aware-snippets:stream-chunk', (_event: IpcRendererEvent, chunk: string) => callback(chunk));
  },

  removeSnippetStatusListener: (callback: (status: string) => void) => {
    ipcRenderer.removeListener('context-aware-snippets:status', (_event: IpcRendererEvent, status: string) => callback(status));
  },

  removeSnippetErrorListener: (callback: (error: string) => void) => {
    ipcRenderer.removeListener('context-aware-snippets:error', (_event: IpcRendererEvent, error: string) => callback(error));
  },

  removeSnippetCompleteListener: (callback: (result: ContextAwareSnippetResult) => void) => {
    ipcRenderer.removeListener('context-aware-snippets:complete', (_event: IpcRendererEvent, result: ContextAwareSnippetResult) => callback(result));
  },
});

// Export individual functions for backward compatibility
export const generateContextAwareSnippet = createContextAwareSnippetsAPI().generateContextAwareSnippet;
export const cancelSnippetGeneration = createContextAwareSnippetsAPI().cancelSnippetGeneration;
export const configureSnippetsService = createContextAwareSnippetsAPI().configureSnippetsService;
export const onSnippetStreamChunk = createContextAwareSnippetsAPI().onSnippetStreamChunk;
export const onSnippetStatus = createContextAwareSnippetsAPI().onSnippetStatus;
export const onSnippetError = createContextAwareSnippetsAPI().onSnippetError;
export const onSnippetComplete = createContextAwareSnippetsAPI().onSnippetComplete;
export const removeSnippetStreamChunkListener = createContextAwareSnippetsAPI().removeSnippetStreamChunkListener;
export const removeSnippetStatusListener = createContextAwareSnippetsAPI().removeSnippetStatusListener;
export const removeSnippetErrorListener = createContextAwareSnippetsAPI().removeSnippetErrorListener;
export const removeSnippetCompleteListener = createContextAwareSnippetsAPI().removeSnippetCompleteListener;

// Note: This module exports functions that are integrated into the main ElectronAPI
// The contextBridge exposure is handled in the main preload/index.ts file
