/**
 * Conflict Predictor API
 * 
 * Provides API interface for Conflict Predictor functionality
 */

import { invokeIpc, createIpcListener } from './ipc-utils';

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
    return createIpcListener('conflict-predictor-event', (event: any) => {
      if (event.type === 'progress' && event.data.status) {
        callback(event.data.status);
      }
    });
  },
  
  onConflictPredictionStatus: (callback: (status: string) => void) => {
    return createIpcListener('conflict-predictor-event', (event: any) => {
      if (event.type === 'progress' && event.data.status) {
        callback(event.data.status);
      }
    });
  },
  
  onConflictPredictionError: (callback: (error: string) => void) => {
    return createIpcListener('conflict-predictor-error', (error: string) => {
      callback(error);
    });
  },
  
  onConflictPredictionComplete: (callback: (result: any) => void) => {
    return createIpcListener('conflict-predictor-complete', (result: any) => {
      callback(result);
    });
  },
  
  onConflictPredictionEvent: (callback: (event: any) => void) => {
    return createIpcListener('conflict-predictor-event', (event: any) => {
      callback(event);
    });
  },
});

export const conflictPredictorAPI: ConflictPredictorAPI = {
  runConflictPrediction: (projectId: string) => 
    invokeIpc('run-conflict-prediction', { projectId }),
  
  cancelConflictPrediction: () => 
    invokeIpc('cancel-conflict-prediction'),
  
  onConflictPredictionStreamChunk: (callback: (chunk: string) => void) => 
    createIpcListener('conflict-predictor-event', (event: any) => {
      if (event.type === 'progress' && event.data.status) {
        callback(event.data.status);
      }
    }),
  
  onConflictPredictionStatus: (callback: (status: string) => void) => 
    createIpcListener('conflict-predictor-event', (event: any) => {
      if (event.type === 'progress' && event.data.status) {
        callback(event.data.status);
      }
    }),
  
  onConflictPredictionError: (callback: (error: string) => void) => 
    createIpcListener('conflict-predictor-error', (error: string) => {
      callback(error);
    }),
  
  onConflictPredictionComplete: (callback: (result: any) => void) => 
    createIpcListener('conflict-predictor-complete', (result: any) => {
      callback(result);
    }),
  
  onConflictPredictionEvent: (callback: (event: any) => void) => 
    createIpcListener('conflict-predictor-event', (event: any) => {
      callback(event);
    }),
};
