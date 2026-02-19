/**
 * Copilot OAuth IPC Handlers
 *
 * IPC handlers for GitHub Copilot OAuth authentication flow.
 * Provides web-based OAuth authentication similar to Claude Code.
 */

import { ipcMain } from 'electron';
import { 
  startCopilotOAuth, 
  handleCopilotOAuthCallback, 
  getCopilotAuthStatus, 
  revokeCopilotAuth 
} from '../copilot-oauth';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';

/**
 * Register Copilot OAuth IPC handlers
 */
export function registerCopilotOAuthHandlers(): void {
  // Start Copilot OAuth flow
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_OAUTH_START,
    async (_event, profileName: string): Promise<IPCResult<{
      success: boolean;
      username?: string;
      profileName?: string;
      error?: string;
    }>> => {
      try {
        console.log('[Copilot OAuth] Starting OAuth flow for profile:', profileName);
        const result = await startCopilotOAuth(profileName);
        return result;
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot OAuth] Failed to start OAuth:', errorMsg);
        return {
          success: false,
          error: `Failed to start OAuth: ${errorMsg}`,
        };
      }
    }
  );

  // Handle OAuth callback
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_OAUTH_CALLBACK,
    async (_event, code: string, state: string, profileName: string): Promise<IPCResult<{
      success: boolean;
      username?: string;
      profileName?: string;
      error?: string;
    }>> => {
      try {
        console.log('[Copilot OAuth] Handling OAuth callback');
        const result = await handleCopilotOAuthCallback(code, state, profileName);
        return result;
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot OAuth] OAuth callback failed:', errorMsg);
        return {
          success: false,
          error: `OAuth callback failed: ${errorMsg}`,
        };
      }
    }
  );

  // Get Copilot authentication status
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_OAUTH_STATUS,
    async (): Promise<IPCResult<{
      authenticated: boolean;
      username?: string;
      profiles: Array<{
        username: string;
        profileName: string;
        createdAt: string;
      }>;
    }>> => {
      try {
        console.log('[Copilot OAuth] Getting auth status');
        const result = await getCopilotAuthStatus();
        return {
          success: true,
          data: result,
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot OAuth] Failed to get auth status:', errorMsg);
        return {
          success: false,
          error: `Failed to get auth status: ${errorMsg}`,
        };
      }
    }
  );

  // Revoke Copilot authentication
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_OAUTH_REVOKE,
    async (_event, username: string): Promise<IPCResult<{
      success: boolean;
      error?: string;
    }>> => {
      try {
        console.log('[Copilot OAuth] Revoking auth for:', username);
        const result = await revokeCopilotAuth(username);
        return result;
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot OAuth] Failed to revoke auth:', errorMsg);
        return {
          success: false,
          error: `Failed to revoke auth: ${errorMsg}`,
        };
      }
    }
  );

  console.log('[IPC] Copilot OAuth handlers registered');
}
