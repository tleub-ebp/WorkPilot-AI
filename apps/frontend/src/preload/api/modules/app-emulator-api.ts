import { ipcRenderer } from 'electron';
import type { AppEmulatorConfig } from '../../../main/app-emulator-service';

export interface AppEmulatorAPI {
  /**
   * Detect project type and configuration
   */
  detectAppProject: (projectDir: string) => Promise<{ success: boolean; data?: AppEmulatorConfig; error?: string }>;

  /**
   * Start the dev server
   */
  startAppEmulator: (config: AppEmulatorConfig) => Promise<{ success: boolean; error?: string }>;

  /**
   * Stop the dev server
   */
  stopAppEmulator: () => Promise<{ success: boolean }>;

  /**
   * Get current emulator status
   */
  getAppEmulatorStatus: () => Promise<{ success: boolean; data?: { running: boolean; url?: string; config?: AppEmulatorConfig } }>;

  /**
   * Listen for status updates
   */
  onAppEmulatorStatus: (callback: (status: string) => void) => () => void;

  /**
   * Listen for server ready (URL available)
   */
  onAppEmulatorReady: (callback: (url: string) => void) => () => void;

  /**
   * Listen for server output lines
   */
  onAppEmulatorOutput: (callback: (line: string) => void) => () => void;

  /**
   * Listen for errors
   */
  onAppEmulatorError: (callback: (error: string) => void) => () => void;

  /**
   * Listen for server stopped
   */
  onAppEmulatorStopped: (callback: () => void) => () => void;

  /**
   * Listen for config detection result
   */
  onAppEmulatorConfig: (callback: (config: AppEmulatorConfig) => void) => () => void;
}

export function createAppEmulatorAPI(): AppEmulatorAPI {
  return {
    detectAppProject: (projectDir: string) => {
      return ipcRenderer.invoke('app-emulator:detect', { projectDir });
    },

    startAppEmulator: (config: AppEmulatorConfig) => {
      return ipcRenderer.invoke('app-emulator:start', { config });
    },

    stopAppEmulator: () => {
      return ipcRenderer.invoke('app-emulator:stop');
    },

    getAppEmulatorStatus: () => {
      return ipcRenderer.invoke('app-emulator:status');
    },

    onAppEmulatorStatus: (callback: (status: string) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, status: string) => callback(status);
      ipcRenderer.on('app-emulator:status-update', handler);
      return () => ipcRenderer.removeListener('app-emulator:status-update', handler);
    },

    onAppEmulatorReady: (callback: (url: string) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, url: string) => callback(url);
      ipcRenderer.on('app-emulator:ready', handler);
      return () => ipcRenderer.removeListener('app-emulator:ready', handler);
    },

    onAppEmulatorOutput: (callback: (line: string) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, line: string) => callback(line);
      ipcRenderer.on('app-emulator:output', handler);
      return () => ipcRenderer.removeListener('app-emulator:output', handler);
    },

    onAppEmulatorError: (callback: (error: string) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, error: string) => callback(error);
      ipcRenderer.on('app-emulator:error', handler);
      return () => ipcRenderer.removeListener('app-emulator:error', handler);
    },

    onAppEmulatorStopped: (callback: () => void) => {
      const handler = () => callback();
      ipcRenderer.on('app-emulator:stopped', handler);
      return () => ipcRenderer.removeListener('app-emulator:stopped', handler);
    },

    onAppEmulatorConfig: (callback: (config: AppEmulatorConfig) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, config: AppEmulatorConfig) => callback(config);
      ipcRenderer.on('app-emulator:config', handler);
      return () => ipcRenderer.removeListener('app-emulator:config', handler);
    },
  };
}
