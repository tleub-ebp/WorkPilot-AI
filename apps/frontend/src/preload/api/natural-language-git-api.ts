import { ipcRenderer } from 'electron';
import { invokeIpc, createIpcListener } from './modules/ipc-utils';

export interface NaturalLanguageGitRequest {
  projectPath: string;
  command: string;
  model?: string;
  thinkingLevel?: string;
}

interface NaturalLanguageGitResult {
  generatedCommand: string;
  explanation: string;
  executionOutput: string;
  success: boolean;
}

export interface NaturalLanguageGitAPI {
  executeNaturalLanguageGit: (request: NaturalLanguageGitRequest) => Promise<void>;
  cancelNaturalLanguageGit: () => Promise<boolean>;
  onNaturalLanguageGitStatus: (callback: (status: string) => void) => () => void;
  onNaturalLanguageGitStreamChunk: (callback: (chunk: string) => void) => () => void;
  onNaturalLanguageGitError: (callback: (error: string) => void) => () => void;
  onNaturalLanguageGitComplete: (callback: (result: NaturalLanguageGitResult) => void) => () => void;
  removeNaturalLanguageGitStatusListener: (callback: (status: string) => void) => void;
  removeNaturalLanguageGitStreamChunkListener: (callback: (chunk: string) => void) => void;
  removeNaturalLanguageGitErrorListener: (callback: (error: string) => void) => void;
  removeNaturalLanguageGitCompleteListener: (callback: (result: NaturalLanguageGitResult) => void) => void;
}

// Track handler wrappers so removeListener can find the correct ipcRenderer handler
const handlerMap = new WeakMap<Function, (...args: unknown[]) => void>();

function registerListener<T extends unknown[]>(channel: string, callback: (...args: T) => void): () => void {
  const handler = (_event: Electron.IpcRendererEvent, ...args: unknown[]) => {
    (callback as (...a: unknown[]) => void)(...args);
  };
  handlerMap.set(callback, handler);
  ipcRenderer.on(channel, handler);
  return () => {
    ipcRenderer.removeListener(channel, handler);
    handlerMap.delete(callback);
  };
}

function removeListener(channel: string, callback: Function): void {
  const handler = handlerMap.get(callback);
  if (handler) {
    ipcRenderer.removeListener(channel, handler);
    handlerMap.delete(callback);
  }
}

export const createNaturalLanguageGitAPI = (): NaturalLanguageGitAPI => ({
  executeNaturalLanguageGit: (request: NaturalLanguageGitRequest) =>
    invokeIpc('execute-natural-language-git', request),
  cancelNaturalLanguageGit: () =>
    invokeIpc('cancel-natural-language-git'),
  onNaturalLanguageGitStatus: (callback: (status: string) => void) =>
    registerListener('natural-language-git-status', callback),
  onNaturalLanguageGitStreamChunk: (callback: (chunk: string) => void) =>
    registerListener('natural-language-git-stream-chunk', callback),
  onNaturalLanguageGitError: (callback: (error: string) => void) =>
    registerListener('natural-language-git-error', callback),
  onNaturalLanguageGitComplete: (callback: (result: NaturalLanguageGitResult) => void) =>
    registerListener('natural-language-git-complete', callback),
  removeNaturalLanguageGitStatusListener: (callback: (status: string) => void) =>
    removeListener('natural-language-git-status', callback),
  removeNaturalLanguageGitStreamChunkListener: (callback: (chunk: string) => void) =>
    removeListener('natural-language-git-stream-chunk', callback),
  removeNaturalLanguageGitErrorListener: (callback: (error: string) => void) =>
    removeListener('natural-language-git-error', callback),
  removeNaturalLanguageGitCompleteListener: (callback: (result: NaturalLanguageGitResult) => void) =>
    removeListener('natural-language-git-complete', callback),
});
