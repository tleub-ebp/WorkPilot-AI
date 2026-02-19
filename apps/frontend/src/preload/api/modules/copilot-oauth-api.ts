/**
 * Copilot OAuth API for renderer process
 *
 * Provides access to GitHub Copilot OAuth authentication:
 * - Start OAuth flow
 * - Get authentication status
 * - Revoke authentication
 */

import { IPC_CHANNELS } from '../../../shared/constants';
import { invokeIpc } from './ipc-utils';

/**
 * Result of OAuth status check
 */
export interface CopilotOAuthStatusResult {
  success: boolean;
  data?: {
    authenticated: boolean;
    profiles: Array<{
      username: string;
      profileName: string;
      createdAt: string;
    }>;
  };
  error?: string;
}

/**
 * Result of starting OAuth flow
 */
export interface CopilotOAuthStartResult {
  success: boolean;
  data?: {
    success: boolean;
    username?: string;
    profileName?: string;
  };
  error?: string;
}

/**
 * Result of revoking OAuth
 */
export interface CopilotOAuthRevokeResult {
  success: boolean;
  error?: string;
}

/**
 * Copilot OAuth API interface exposed to renderer
 */
export interface CopilotOAuthAPI {
  /**
   * Get Copilot OAuth authentication status
   * Returns authentication status and list of profiles
   */
  invoke: (channel: string, ...args: any[]) => Promise<any>;

  /**
   * Start Copilot OAuth flow
   * Initiates web-based OAuth authentication
   */
  copilotOAuthStart: (profileName: string) => Promise<CopilotOAuthStartResult>;

  /**
   * Get Copilot OAuth status
   * Check current authentication status
   */
  copilotOAuthStatus: () => Promise<CopilotOAuthStatusResult>;

  /**
   * Revoke Copilot OAuth authentication
   * Remove authentication for a specific username
   */
  copilotOAuthRevoke: (username: string) => Promise<CopilotOAuthRevokeResult>;
}

/**
 * Creates the Copilot OAuth API implementation
 */
export const createCopilotOAuthAPI = (): CopilotOAuthAPI => ({
  invoke: (channel: string, ...args: any[]) => invokeIpc(channel, ...args),

  copilotOAuthStart: (profileName: string): Promise<CopilotOAuthStartResult> =>
    invokeIpc(IPC_CHANNELS.COPILOT_OAUTH_START, profileName),

  copilotOAuthStatus: (): Promise<CopilotOAuthStatusResult> =>
    invokeIpc(IPC_CHANNELS.COPILOT_OAUTH_STATUS),

  copilotOAuthRevoke: (username: string): Promise<CopilotOAuthRevokeResult> =>
    invokeIpc(IPC_CHANNELS.COPILOT_OAUTH_REVOKE, username),
});
