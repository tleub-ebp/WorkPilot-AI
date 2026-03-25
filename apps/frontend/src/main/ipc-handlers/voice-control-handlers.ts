import { ipcMain } from 'electron';
import { voiceControlService } from '../voice-control-service';
import type { VoiceControlRequest } from '../voice-control-service';

/**
 * Register IPC handlers for voice control functionality
 */
export function registerVoiceControlHandlers(): void {
  // Start voice recording
  ipcMain.handle('voice-control:startRecording', async (_event, request?: VoiceControlRequest) => {
    try {
      await voiceControlService.startRecording(request);
      return { success: true };
    } catch (error) {
      console.error('[VoiceControl] Failed to start recording:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  // Stop voice recording
  ipcMain.handle('voice-control:stopRecording', async () => {
    try {
      voiceControlService.stopRecording();
      return { success: true };
    } catch (error) {
      console.error('[VoiceControl] Failed to stop recording:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  // Cancel voice control
  ipcMain.handle('voice-control:cancel', async () => {
    try {
      const cancelled = voiceControlService.cancel();
      return { success: true, cancelled };
    } catch (error) {
      console.error('[VoiceControl] Failed to cancel:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  // Check if voice control is active
  ipcMain.handle('voice-control:isActive', async () => {
    try {
      const isActive = voiceControlService.isActive();
      return { success: true, isActive };
    } catch (error) {
      console.error('[VoiceControl] Failed to check status:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  // Configure voice control service
  ipcMain.handle('voice-control:configure', async (_event, config: { pythonPath?: string; autoBuildSourcePath?: string }) => {
    try {
      voiceControlService.configure(config.pythonPath, config.autoBuildSourcePath);
      return { success: true };
    } catch (error) {
      console.error('[VoiceControl] Failed to configure:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });
}

/**
 * Setup event forwarding from voice control service to renderer
 */
export function setupVoiceControlEvents(): void {
  // Forward status updates
  voiceControlService.on('status', (status: string) => {
    const windows = require('electron').BrowserWindow.getAllWindows();
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    windows.forEach((window: any) => {
      if (!window.isDestroyed()) {
        window.webContents.send('voice-control:status', status);
      }
    });
  });

  // Forward streaming chunks
  voiceControlService.on('stream-chunk', (chunk: string) => {
    const windows = require('electron').BrowserWindow.getAllWindows();
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    windows.forEach((window: any) => {
      if (!window.isDestroyed()) {
        window.webContents.send('voice-control:stream-chunk', chunk);
      }
    });
  });

  // Forward errors
  voiceControlService.on('error', (error: string) => {
    const windows = require('electron').BrowserWindow.getAllWindows();
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    windows.forEach((window: any) => {
      if (!window.isDestroyed()) {
        window.webContents.send('voice-control:error', error);
      }
    });
  });

  // Forward completion results
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  voiceControlService.on('complete', (result: any) => {
    const windows = require('electron').BrowserWindow.getAllWindows();
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    windows.forEach((window: any) => {
      if (!window.isDestroyed()) {
        window.webContents.send('voice-control:complete', result);
      }
    });
  });

  // Forward audio level updates
  voiceControlService.on('audio-level', (level: number) => {
    const windows = require('electron').BrowserWindow.getAllWindows();
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    windows.forEach((window: any) => {
      if (!window.isDestroyed()) {
        window.webContents.send('voice-control:audio-level', level);
      }
    });
  });

  // Forward duration updates
  voiceControlService.on('duration', (duration: number) => {
    const windows = require('electron').BrowserWindow.getAllWindows();
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    windows.forEach((window: any) => {
      if (!window.isDestroyed()) {
        window.webContents.send('voice-control:duration', duration);
      }
    });
  });
}
