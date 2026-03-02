/**
 * Smart Estimation API
 * 
 * Provides API interface for Smart Estimation functionality
 */

export interface SmartEstimationAPI {
  runSmartEstimation: (projectId: string, taskDescription: string) => Promise<void>;
  cancelSmartEstimation: () => Promise<boolean>;
  onSmartEstimationStreamChunk: (callback: (chunk: string) => void) => () => void;
  onSmartEstimationStatus: (callback: (status: string) => void) => () => void;
  onSmartEstimationError: (callback: (error: string) => void) => () => void;
  onSmartEstimationComplete: (callback: (result: any) => void) => () => void;
  onSmartEstimationEvent: (callback: (event: any) => void) => () => void;
}

declare global {
  interface Window {
    electronAPI: {
      runSmartEstimation: (projectId: string, taskDescription: string) => Promise<void>;
      cancelSmartEstimation: () => Promise<boolean>;
      onSmartEstimationStreamChunk: (callback: (chunk: string) => void) => () => void;
      onSmartEstimationStatus: (callback: (status: string) => void) => () => void;
      onSmartEstimationError: (callback: (error: string) => void) => () => void;
      onSmartEstimationComplete: (callback: (result: any) => void) => () => void;
      onSmartEstimationEvent: (callback: (event: any) => void) => () => void;
    };
  }
}

export const smartEstimationAPI: SmartEstimationAPI = {
  runSmartEstimation: (projectId: string, taskDescription: string) => 
    window.electronAPI.runSmartEstimation(projectId, taskDescription),
  
  cancelSmartEstimation: () => 
    window.electronAPI.cancelSmartEstimation(),
  
  onSmartEstimationStreamChunk: (callback: (chunk: string) => void) => 
    window.electronAPI.onSmartEstimationStreamChunk(callback),
  
  onSmartEstimationStatus: (callback: (status: string) => void) => 
    window.electronAPI.onSmartEstimationStatus(callback),
  
  onSmartEstimationError: (callback: (error: string) => void) => 
    window.electronAPI.onSmartEstimationError(callback),
  
  onSmartEstimationComplete: (callback: (result: any) => void) => 
    window.electronAPI.onSmartEstimationComplete(callback),
  
  onSmartEstimationEvent: (callback: (event: any) => void) => 
    window.electronAPI.onSmartEstimationEvent(callback),
};
