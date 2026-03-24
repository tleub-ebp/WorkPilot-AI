/**
 * GitHub Copilot OAuth Authentication
 *
 * Implements OAuth flow for GitHub Copilot similar to Claude Code OAuth.
 * Uses GitHub OAuth to get access tokens for Copilot API access.
 *
 * Flow:
 * 1. Generate GitHub OAuth state
 * 2. Open browser for GitHub OAuth authorization
 * 3. Handle OAuth callback with authorization code
 * 4. Exchange code for access token
 * 5. Store token in keychain for future use
 */

import { randomBytes } from 'crypto';
import { promisify } from 'util';
import { execFile } from 'child_process';
import path from 'path';
import os from 'os';
import { app } from 'electron';
import { isWindows } from './platform';

const _execFileAsync = promisify(execFile);

// GitHub OAuth configuration
const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || 'Ov23liF2F5qF1M2x0v3K'; // Default Copilot client ID
const GITHUB_OAUTH_SCOPES = [
  'repo',           // Repository access
  'read:user',      // Read user profile
  'user:email',     // Read user email
  'copilot',        // Copilot access (if available)
].join(' ');

// Copilot OAuth redirect URI (localhost for development)
const OAUTH_REDIRECT_URI = 'http://localhost:3000/oauth/callback';
const OAUTH_STATE_LENGTH = 32;

/**
 * Generate a secure random state parameter for OAuth
 */
function generateOAuthState(): string {
  return randomBytes(OAUTH_STATE_LENGTH).toString('hex');
}

/**
 * Build GitHub OAuth authorization URL
 */
function buildOAuthUrl(state: string): string {
  const params = new URLSearchParams({
    client_id: GITHUB_CLIENT_ID,
    redirect_uri: OAUTH_REDIRECT_URI,
    scope: GITHUB_OAUTH_SCOPES,
    state: state,
    response_type: 'code',
    allow_signup: 'true',
  });

  return `https://github.com/login/oauth/authorize?${params.toString()}`;
}

/**
 * Open browser for OAuth authorization
 */
async function openOAuthBrowser(url: string): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    try {
      if (isWindows()) {
        const { exec } = require('child_process');
        // Use exec with shell: true to properly handle URL with parameters
        exec(`start "" "${url}"`, (error: Error | null) => {
          if (error) reject(error);
          else resolve();
        });
      } else if (process.platform === 'darwin') {
        execFile('open', [url], (error) => {
          if (error) reject(error);
          else resolve();
        });
      } else {
        execFile('xdg-open', [url], (error) => {
          if (error) reject(error);
          else resolve();
        });
      }
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Exchange OAuth authorization code for access token
 */
async function exchangeCodeForToken(code: string): Promise<{
  access_token: string;
  token_type: string;
  scope: string;
}> {
  const response = await fetch('https://github.com/login/oauth/access_token', {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      client_id: GITHUB_CLIENT_ID,
      client_secret: process.env.GITHUB_CLIENT_SECRET || '', // Should be configured
      code: code,
      redirect_uri: OAUTH_REDIRECT_URI,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`GitHub OAuth token exchange failed: ${response.status} ${errorText}`);
  }

  const data = await response.json();
  
  if (data.error) {
    throw new Error(`GitHub OAuth error: ${data.error_description || data.error}`);
  }

  return data;
}

/**
 * Get GitHub user profile using access token
 */
async function getGitHubUserProfile(accessToken: string): Promise<{
  login: string;
  name: string | null;
  email: string | null;
  avatar_url: string;
}> {
  const response = await fetch('https://api.github.com/user', {
    headers: {
      'Authorization': `token ${accessToken}`,
      'User-Agent': 'WorkPilot-AI',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to get GitHub user profile: ${response.status}`);
  }

  return await response.json();
}

/**
 * Check Copilot access by exchanging the GitHub token for a Copilot session token.
 * The token-exchange endpoint returns 200 only when the account has an active Copilot subscription.
 */
async function checkCopilotAccess(accessToken: string): Promise<boolean> {
  try {
    const response = await fetch('https://api.github.com/copilot_internal/v2/token', {
      headers: {
        'Authorization': `token ${accessToken}`,
        'editor-version': 'vscode/1.95.3',
        'editor-plugin-version': 'copilot-chat/0.22.4',
        'user-agent': 'GitHubCopilotChat/0.22.4',
      },
    });
    return response.ok;
  } catch (error) {
    console.warn('[Copilot OAuth] Copilot access check failed:', error);
    return false;
  }
}

/**
 * Store Copilot OAuth token in system keychain
 */
async function storeCopilotToken(
  username: string,
  accessToken: string,
  profileName: string
): Promise<void> {
  const configDir = path.join(os.homedir(), '.workpilot', 'copilot-profiles');
  
  // For now, we'll store in a simple file
  // In production, this should use the system keychain like Claude OAuth
  const tokenFile = path.join(configDir, `${username}.json`);
  
  try {
    await require('fs').promises.mkdir(configDir, { recursive: true });
    
    const tokenData = {
      username,
      accessToken,
      profileName,
      createdAt: new Date().toISOString(),
      provider: 'copilot',
    };
    
    await require('fs').promises.writeFile(tokenFile, JSON.stringify(tokenData, null, 2));
  } catch (error) {
    throw new Error(`Failed to store Copilot token: ${error}`);
  }
}

/**
 * Get stored Copilot OAuth token
 */
async function getCopilotToken(username: string): Promise<{
  username: string;
  accessToken: string;
  profileName: string;
  createdAt: string;
} | null> {
  const configDir = path.join(os.homedir(), '.workpilot', 'copilot-profiles');
  const tokenFile = path.join(configDir, `${username}.json`);
  
  try {
    const data = await require('fs').promises.readFile(tokenFile, 'utf-8');
    return JSON.parse(data);
  } catch (_error) {
    return null;
  }
}

/**
 * Start GitHub Copilot OAuth flow
 */
export async function startCopilotOAuth(profileName: string): Promise<{
  success: boolean;
  username?: string;
  profileName?: string;
  error?: string;
}> {
  try {
    
    // Generate state and build OAuth URL
    const state = generateOAuthState();
    const oauthUrl = buildOAuthUrl(state);
    
    // Store state for callback verification
    const stateFile = path.join(app.getPath('temp'), 'copilot-oauth-state.txt');
    await require('fs').promises.writeFile(stateFile, state);
    
    // Open browser for OAuth
    await openOAuthBrowser(oauthUrl);
    
    return {
      success: true,
      profileName,
    };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Unknown error';
    console.error('[Copilot OAuth] Failed to start OAuth:', errorMsg);
    return {
      success: false,
      error: `Failed to start OAuth: ${errorMsg}`,
    };
  }
}

/**
 * Handle OAuth callback from GitHub
 */
export async function handleCopilotOAuthCallback(
  code: string,
  state: string,
  profileName: string
): Promise<{
  success: boolean;
  username?: string;
  profileName?: string;
  error?: string;
}> {
  try {
    
    // Verify state
    const stateFile = path.join(app.getPath('temp'), 'copilot-oauth-state.txt');
    try {
      const storedState = await require('fs').promises.readFile(stateFile, 'utf-8');
      if (storedState !== state) {
        throw new Error('Invalid OAuth state');
      }
      // Clean up state file
      await require('fs').promises.unlink(stateFile);
    } catch (_error) {
      throw new Error('Invalid or missing OAuth state');
    }
    
    // Exchange code for access token
    const tokenData = await exchangeCodeForToken(code);
    
    // Get user profile
    const userProfile = await getGitHubUserProfile(tokenData.access_token);
    
    // Check Copilot access
    const hasCopilotAccess = await checkCopilotAccess(tokenData.access_token);
    if (!hasCopilotAccess) {
      console.warn('[Copilot OAuth] Warning: Copilot access not confirmed, but proceeding');
    }
    
    // Store token
    await storeCopilotToken(userProfile.login, tokenData.access_token, profileName);
    
    return {
      success: true,
      username: userProfile.login,
      profileName,
    };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Unknown error';
    console.error('[Copilot OAuth] OAuth callback failed:', errorMsg);
    return {
      success: false,
      error: `OAuth callback failed: ${errorMsg}`,
    };
  }
}

/**
 * Get Copilot authentication status
 */
export async function getCopilotAuthStatus(): Promise<{
  authenticated: boolean;
  username?: string;
  profiles: Array<{
    username: string;
    profileName: string;
    createdAt: string;
  }>;
}> {
  try {
    const configDir = path.join(os.homedir(), '.workpilot', 'copilot-profiles');
    
    try {
      const files = await require('fs').promises.readdir(configDir);
      const profiles: Array<{
        username: string;
        profileName: string;
        createdAt: string;
      }> = [];
      
      for (const file of files) {
        if (file.endsWith('.json')) {
          try {
            const tokenData = await getCopilotToken(file.replace('.json', ''));
            if (tokenData) {
              profiles.push({
                username: tokenData.username,
                profileName: tokenData.profileName,
                createdAt: tokenData.createdAt,
              });
            }
          } catch (_error) {
          }
        }
      }
      
      return {
        authenticated: profiles.length > 0,
        profiles,
      };
    } catch (_error) {
      return {
        authenticated: false,
        profiles: [],
      };
    }
  } catch (_error) {
    return {
      authenticated: false,
      profiles: [],
    };
  }
}

/**
 * Revoke Copilot authentication
 */
export async function revokeCopilotAuth(username: string): Promise<{
  success: boolean;
  error?: string;
}> {
  try {
    const tokenData = await getCopilotToken(username);
    if (!tokenData) {
      return {
        success: false,
        error: 'No authentication found for this user',
      };
    }
    
    // Try to revoke the token (GitHub doesn't have a direct revoke endpoint for OAuth tokens)
    // We'll just delete the stored token
    const configDir = path.join(os.homedir(), '.workpilot', 'copilot-profiles');
    const tokenFile = path.join(configDir, `${username}.json`);
    
    await require('fs').promises.unlink(tokenFile);
    
    return {
      success: true,
    };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Unknown error';
    console.error('[Copilot OAuth] Failed to revoke auth:', errorMsg);
    return {
      success: false,
      error: `Failed to revoke authentication: ${errorMsg}`,
    };
  }
}
