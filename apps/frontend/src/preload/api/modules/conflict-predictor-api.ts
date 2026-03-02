/**
 * Conflict Predictor API
 * 
 * Provides API interface for Conflict Predictor functionality
 */

import { invokeIpc } from './ipc-utils';

export interface ConflictPredictorAPI {
  runConflictPrediction: (projectId: string) => Promise<void>;
  cancelConflictPrediction: () => Promise<boolean>;
  onConflictPredictionStreamChunk: (callback: (chunk: string) => void) => () => void;
  onConflictPredictionStatus: (callback: (status: string) => void) => () => void;
  onConflictPredictionError: (callback: (error: string) => void) => () => void;
  onConflictPredictionComplete: (callback: (result: any) => void) => () => void;
  onConflictPredictionEvent: (callback: (event: any) => void) => () => void;
}

export const createConflictPredictorAPI = (): ConflictPredictorAPI => ({
  runConflictPrediction: (projectId: string) => 
    invokeIpc('run-conflict-prediction', { projectId }),
  
  cancelConflictPrediction: () => 
    invokeIpc('cancel-conflict-prediction'),
  
  onConflictPredictionStreamChunk: (callback: (chunk: string) => void) => {
    const unsubscribe = window.electronAPI.onConflictPredictionEvent?.((event: any) => {
      if (event.type === 'progress' && event.data.status) {
        callback(event.data.status);
      }
    });
    return unsubscribe || (() => {});
  },
  
  onConflictPredictionStatus: (callback: (status: string) => void) => {
    const unsubscribe = window.electronAPI.onConflictPredictionEvent?.((event: any) => {
      if (event.type === 'progress' && event.data.status) {
        callback(event.data.status);
      }
    });
    return unsubscribe || (() => {});
  },
  
  onConflictPredictionError: (callback: (error: string) => void) => {
    const unsubscribe = window.electronAPI.onConflictPredictionError?.(callback);
    return unsubscribe || (() => {});
  },
  
  onConflictPredictionComplete: (callback: (result: any) => void) => {
    const unsubscribe = window.electronAPI.onConflictPredictionComplete?.(callback);
    return unsubscribe || (() => {});
  },
  
  onConflictPredictionEvent: (callback: (event: any) => void) => {
    const unsubscribe = window.electronAPI.onConflictPredictionEvent?.(callback);
    return unsubscribe || (() => {});
  },
});

export const conflictPredictorAPI: ConflictPredictorAPI = {
  runConflictPrediction: (projectId: string) => 
    window.electronAPI.runConflictPrediction(projectId),
  
  cancelConflictPrediction: () => 
    window.electronAPI.cancelConflictPrediction(),
  
  onConflictPredictionStreamChunk: (callback: (chunk: string) => void) => 
    window.electronAPI.onConflictPredictionStreamChunk(callback),
  
  onConflictPredictionStatus: (callback: (status: string) => void) => 
    window.electronAPI.onConflictPredictionStatus(callback),
  
  onConflictPredictionError: (callback: (error: string) => void) => 
    window.electronAPI.onConflictPredictionError(callback),
  
  onConflictPredictionComplete: (callback: (result: any) => void) => 
    window.electronAPI.onConflictPredictionComplete(callback),
  
  onConflictPredictionEvent: (callback: (event: any) => void) => 
    window.electronAPI.onConflictPredictionEvent(callback),
};
