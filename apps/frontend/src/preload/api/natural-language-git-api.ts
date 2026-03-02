import { invokeIpc } from './modules/ipc-utils';
import type { IPCResult } from '../../shared/types';

export interface NaturalLanguageGitRequest {
  projectPath: string;
  command: string;
  model?: string;
  thinkingLevel?: string;
}

export interface NaturalLanguageGitAPI {
  executeNaturalLanguageGit: (request: NaturalLanguageGitRequest) => Promise<void>;
  cancelNaturalLanguageGit: () => Promise<boolean>;
  onNaturalLanguageGitStatus: (callback: (status: string) => void) => () => void;
  onNaturalLanguageGitStreamChunk: (callback: (chunk: string) => void) => () => void;
  onNaturalLanguageGitError: (callback: (error: string) => void) => () => void;
  onNaturalLanguageGitComplete: (callback: (result: {
    generatedCommand: string;
    explanation: string;
    executionOutput: string;
    success: boolean;
  }) => void) => () => void;
  removeNaturalLanguageGitStatusListener: (callback: (status: string) => void) => void;
  removeNaturalLanguageGitStreamChunkListener: (callback: (chunk: string) => void) => void;
  removeNaturalLanguageGitErrorListener: (callback: (error: string) => void) => void;
  removeNaturalLanguageGitCompleteListener: (callback: (result: {
    generatedCommand: string;
    explanation: string;
    executionOutput: string;
    success: boolean;
  }) => void) => void;
}

export const createNaturalLanguageGitAPI = (): NaturalLanguageGitAPI => ({
  executeNaturalLanguageGit: (request: NaturalLanguageGitRequest) => 
    invokeIpc('execute-natural-language-git', request),
  cancelNaturalLanguageGit: () => 
    invokeIpc('cancel-natural-language-git'),
  onNaturalLanguageGitStatus: (callback: (status: string) => void) => {
    window.electronAPI?.on('natural-language-git-status', callback);
    return () => {
      window.electronAPI?.removeEventListener('natural-language-git-status', callback);
    };
  },
  onNaturalLanguageGitStreamChunk: (callback: (chunk: string) => void) => {
    window.electronAPI?.on('natural-language-git-stream-chunk', callback);
    return () => {
      window.electronAPI?.removeEventListener('natural-language-git-stream-chunk', callback);
    };
  },
  onNaturalLanguageGitError: (callback: (error: string) => void) => {
    window.electronAPI?.on('natural-language-git-error', callback);
    return () => {
      window.electronAPI?.removeEventListener('natural-language-git-error', callback);
    };
  },
  onNaturalLanguageGitComplete: (callback: (result: {
    generatedCommand: string;
    explanation: string;
    executionOutput: string;
    success: boolean;
  }) => void) => {
    window.electronAPI?.on('natural-language-git-complete', callback);
    return () => {
      window.electronAPI?.removeEventListener('natural-language-git-complete', callback);
    };
  },
  removeNaturalLanguageGitStatusListener: (callback: (status: string) => void) => {
    window.electronAPI?.removeEventListener('natural-language-git-status', callback);
  },
  removeNaturalLanguageGitStreamChunkListener: (callback: (chunk: string) => void) => {
    window.electronAPI?.removeEventListener('natural-language-git-stream-chunk', callback);
  },
  removeNaturalLanguageGitErrorListener: (callback: (error: string) => void) => {
    window.electronAPI?.removeEventListener('natural-language-git-error', callback);
  },
  removeNaturalLanguageGitCompleteListener: (callback: (result: {
    generatedCommand: string;
    explanation: string;
    executionOutput: string;
    success: boolean;
  }) => void) => {
    window.electronAPI?.removeEventListener('natural-language-git-complete', callback);
  },
});
