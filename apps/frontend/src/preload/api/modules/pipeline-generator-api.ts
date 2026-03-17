/**
 * Pipeline Generator API module
 */

import type { CiPlatform, PipelineGeneratorRequest, PipelineGeneratorResult } from '../../../main/pipeline-generator-service';

export type { CiPlatform, PipelineGeneratorRequest, PipelineGeneratorResult };

export interface PipelineGeneratorAPI {
  generatePipelines: (request: PipelineGeneratorRequest) => Promise<{ success: boolean; error?: string }>;
  cancelPipelineGeneration: () => Promise<{ success: boolean; cancelled: boolean; error?: string }>;
  configurePipelineGenerator: (config: { pythonPath?: string; autoBuildSourcePath?: string }) => Promise<{ success: boolean; error?: string }>;
  onPipelineGeneratorStatus: (callback: (status: string) => void) => () => void;
  onPipelineGeneratorStreamChunk: (callback: (chunk: string) => void) => () => void;
  onPipelineGeneratorError: (callback: (error: string) => void) => () => void;
  onPipelineGeneratorComplete: (callback: (result: PipelineGeneratorResult) => void) => () => void;
}

export function createPipelineGeneratorAPI(): PipelineGeneratorAPI {
  return {
    generatePipelines: (request) =>
      globalThis.electronAPI.invoke('pipelineGenerator:generate', request),
    cancelPipelineGeneration: () =>
      globalThis.electronAPI.invoke('pipelineGenerator:cancel'),
    configurePipelineGenerator: (config) =>
      globalThis.electronAPI.invoke('pipelineGenerator:configure', config),
    onPipelineGeneratorStatus: (callback) =>
      globalThis.electronAPI.on('pipelineGenerator:status', callback),
    onPipelineGeneratorStreamChunk: (callback) =>
      globalThis.electronAPI.on('pipelineGenerator:streamChunk', callback),
    onPipelineGeneratorError: (callback) =>
      globalThis.electronAPI.on('pipelineGenerator:error', callback),
    onPipelineGeneratorComplete: (callback) =>
      globalThis.electronAPI.on('pipelineGenerator:complete', callback),
  };
}
