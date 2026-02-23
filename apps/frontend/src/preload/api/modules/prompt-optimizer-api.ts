import { IPC_CHANNELS } from '../../../shared/constants';
import { createIpcListener, sendIpc, IpcListenerCleanup } from './ipc-utils';

/**
 * Result of prompt optimization
 */
export interface PromptOptimizerResult {
  optimized: string;
  changes: string[];
  reasoning: string;
}

/**
 * Prompt Optimizer API operations
 */
export interface PromptOptimizerAPI {
  // Operations
  optimizePrompt: (
    projectId: string,
    prompt: string,
    agentType: 'analysis' | 'coding' | 'verification' | 'general'
  ) => void;

  // Event Listeners
  onPromptOptimizerStreamChunk: (
    callback: (chunk: string) => void
  ) => IpcListenerCleanup;
  onPromptOptimizerStatus: (
    callback: (status: string) => void
  ) => IpcListenerCleanup;
  onPromptOptimizerError: (
    callback: (error: string) => void
  ) => IpcListenerCleanup;
  onPromptOptimizerComplete: (
    callback: (result: PromptOptimizerResult) => void
  ) => IpcListenerCleanup;
}

/**
 * Creates the Prompt Optimizer API implementation
 */
export const createPromptOptimizerAPI = (): PromptOptimizerAPI => ({
  // Operations
  optimizePrompt: (
    projectId: string,
    prompt: string,
    agentType: 'analysis' | 'coding' | 'verification' | 'general'
  ): void =>
    sendIpc(IPC_CHANNELS.PROMPT_OPTIMIZER_OPTIMIZE, projectId, prompt, agentType),

  // Event Listeners
  onPromptOptimizerStreamChunk: (
    callback: (chunk: string) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.PROMPT_OPTIMIZER_STREAM_CHUNK, callback),

  onPromptOptimizerStatus: (
    callback: (status: string) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.PROMPT_OPTIMIZER_STATUS, callback),

  onPromptOptimizerError: (
    callback: (error: string) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.PROMPT_OPTIMIZER_ERROR, callback),

  onPromptOptimizerComplete: (
    callback: (result: PromptOptimizerResult) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.PROMPT_OPTIMIZER_COMPLETE, callback),
});
