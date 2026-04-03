/**
 * Live Development Companion IPC handlers registration
 *
 * Handles IPC communication between the renderer process and the
 * Live Companion service for real-time pair programming.
 */

import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import { liveCompanionService } from '../live-companion-service';
import { safeSendToRenderer } from './utils';

/**
 * Register all live-companion-related IPC handlers
 */
export function registerLiveCompanionHandlers(
  getMainWindow: () => BrowserWindow | null
): () => void {
  // ============================================
  // Lifecycle operations
  // ============================================

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_START, async (_event, projectDir: string) => {
    try {
      const success = await liveCompanionService.start(projectDir);
      return { success };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_STOP, async () => {
    try {
      liveCompanionService.stop();
      return { success: true };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_GET_STATE, async () => {
    return { success: true, data: liveCompanionService.getState() };
  });

  // ============================================
  // Suggestion operations
  // ============================================

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_GET_SUGGESTIONS, async () => {
    try {
      return { success: true, data: liveCompanionService.getSuggestions() };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_DISMISS_SUGGESTION, async (_event, suggestionId: string) => {
    try {
      const result = liveCompanionService.dismissSuggestion(suggestionId);
      return { success: result };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_APPLY_SUGGESTION, async (_event, suggestionId: string) => {
    try {
      const result = liveCompanionService.applySuggestion(suggestionId);
      return { success: result };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  // ============================================
  // Takeover operations
  // ============================================

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_GET_TAKEOVERS, async () => {
    try {
      return { success: true, data: liveCompanionService.getTakeovers() };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_ACCEPT_TAKEOVER, async (_event, proposalId: string) => {
    try {
      const result = liveCompanionService.acceptTakeover(proposalId);
      return { success: result };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_DECLINE_TAKEOVER, async (_event, proposalId: string) => {
    try {
      const result = liveCompanionService.declineTakeover(proposalId);
      return { success: result };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  // ============================================
  // Config operations
  // ============================================

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_GET_CONFIG, async () => {
    return { success: true, data: liveCompanionService.getConfig() };
  });

  ipcMain.handle(IPC_CHANNELS.LIVE_COMPANION_UPDATE_CONFIG, async (_event, updates: Record<string, unknown>) => {
    try {
      const config = liveCompanionService.updateConfig(updates);
      return { success: true, data: config };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  // ============================================
  // Service events → Renderer
  // ============================================

  const handleStateChanged = (state: unknown): void => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.LIVE_COMPANION_STATE_CHANGED, state);
  };

  const handleSuggestion = (suggestion: unknown): void => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.LIVE_COMPANION_SUGGESTION, suggestion);
  };

  const handleTakeoverProposal = (proposal: unknown): void => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.LIVE_COMPANION_TAKEOVER_PROPOSAL, proposal);
  };

  const handleFileChange = (event: unknown): void => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.LIVE_COMPANION_FILE_CHANGE, event);
  };

  const handleError = (error: string): void => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.LIVE_COMPANION_ERROR, error);
  };

  liveCompanionService.on('state-changed', handleStateChanged);
  liveCompanionService.on('suggestion', handleSuggestion);
  liveCompanionService.on('takeover-proposal', handleTakeoverProposal);
  liveCompanionService.on('file-change', handleFileChange);
  liveCompanionService.on('error', handleError);

  // Return cleanup function
  return (): void => {
    liveCompanionService.off('state-changed', handleStateChanged);
    liveCompanionService.off('suggestion', handleSuggestion);
    liveCompanionService.off('takeover-proposal', handleTakeoverProposal);
    liveCompanionService.off('file-change', handleFileChange);
    liveCompanionService.off('error', handleError);
  };
}
