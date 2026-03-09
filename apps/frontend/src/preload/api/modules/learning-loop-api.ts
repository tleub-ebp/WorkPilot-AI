/**
 * Learning Loop API module
 *
 * Provides API methods for interacting with the Autonomous Agent Learning Loop.
 */

import type {
  LearningPattern,
  LearningSummary,
  LearningLoopCompleteResult,
} from '../../../shared/types/learning-loop';

export interface LearningLoopAPI {
  // Operations
  getLearningPatterns: (projectId: string) => Promise<{ success: boolean; data?: LearningPattern[]; error?: string }>;
  getLearningSummary: (projectId: string) => Promise<{ success: boolean; data?: LearningSummary; error?: string }>;
  runLearningAnalysis: (projectId: string, specId?: string) => void;
  stopLearningAnalysis: () => Promise<{ success: boolean; cancelled: boolean; error?: string }>;
  deleteLearningPattern: (projectId: string, patternId: string) => Promise<{ success: boolean; error?: string }>;
  toggleLearningPattern: (projectId: string, patternId: string) => Promise<{ success: boolean; data?: boolean; error?: string }>;

  // Event listeners
  onLearningLoopStatus: (callback: (status: string) => void) => () => void;
  onLearningLoopStreamChunk: (callback: (chunk: string) => void) => () => void;
  onLearningLoopError: (callback: (error: string) => void) => () => void;
  onLearningLoopComplete: (callback: (result: LearningLoopCompleteResult) => void) => () => void;
}

/**
 * Create the Learning Loop API object
 */
export function createLearningLoopAPI(): LearningLoopAPI {
  return {
    // Operations
    getLearningPatterns: (projectId: string) =>
      window.electronAPI.invoke('learningLoop:getPatterns', projectId),

    getLearningSummary: (projectId: string) =>
      window.electronAPI.invoke('learningLoop:getSummary', projectId),

    runLearningAnalysis: (projectId: string, specId?: string) =>
      window.electronAPI.send('learningLoop:runAnalysis', projectId, specId),

    stopLearningAnalysis: () =>
      window.electronAPI.invoke('learningLoop:stopAnalysis'),

    deleteLearningPattern: (projectId: string, patternId: string) =>
      window.electronAPI.invoke('learningLoop:deletePattern', projectId, patternId),

    toggleLearningPattern: (projectId: string, patternId: string) =>
      window.electronAPI.invoke('learningLoop:togglePattern', projectId, patternId),

    // Event listeners
    onLearningLoopStatus: (callback: (status: string) => void) =>
      window.electronAPI.on('learningLoop:status', callback),

    onLearningLoopStreamChunk: (callback: (chunk: string) => void) =>
      window.electronAPI.on('learningLoop:streamChunk', callback),

    onLearningLoopError: (callback: (error: string) => void) =>
      window.electronAPI.on('learningLoop:error', callback),

    onLearningLoopComplete: (callback: (result: LearningLoopCompleteResult) => void) =>
      window.electronAPI.on('learningLoop:complete', callback),
  };
}
