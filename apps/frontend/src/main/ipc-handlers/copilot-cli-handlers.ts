/**
 * Copilot CLI Handlers
 *
 * IPC handlers for GitHub Copilot CLI (gh copilot) version checking, installation, and auth.
 * Mirrors the Claude Code CLI handler pattern but adapted for the gh extension model.
 *
 * Key differences from Claude Code:
 * - Copilot CLI is a GitHub CLI extension (`gh copilot`), not a standalone binary
 * - Installation: `gh extension install github/gh-copilot`
 * - Auth: `gh auth login` (OAuth via GitHub CLI)
 * - Version registry: GitHub releases (github/gh-copilot), not npm
 */

import { ipcMain } from 'electron';
import { execFile, spawn } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';
import { promisify } from 'util';
import { IPC_CHANNELS, DEFAULT_APP_SETTINGS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import type { CopilotCliVersionInfo, CopilotInstallationList, CopilotInstallationInfo } from '../../shared/types/cli';
import { getToolInfo, getToolPath, configureTools } from '../cli-tool-manager';
import { readSettingsFile, writeSettingsFile } from '../settings-utils';
import { isSecurePath } from '../utils/windows-paths';
import { isWindows } from '../platform';
import { getAugmentedEnv } from '../env-utils';

const execFileAsync = promisify(execFile);

// Cache for latest copilot version
let cachedLatestCopilotVersion: { version: string; timestamp: number } | null = null;
const COPILOT_CACHE_DURATION_MS = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Validate a Copilot CLI (gh) path and get copilot extension version
 * @param ghPath - Path to the gh CLI executable
 * @returns Tuple of [isValid, copilotVersion or null, ghVersion or null]
 */
async function validateCopilotCliAsync(ghPath: string): Promise<[boolean, string | null, string | null]> {
  try {
    if (isWindows() && !isSecurePath(ghPath)) {
      throw new Error(`gh CLI path failed security validation: ${ghPath}`);
    }

    const env = getAugmentedEnv();

    // Get gh version
    let ghVersion: string | null = null;
    try {
      const ghResult = await execFileAsync(ghPath, ['--version'], {
        encoding: 'utf-8',
        timeout: 5000,
        windowsHide: true,
        env,
      });
      const ghMatch = ghResult.stdout.match(/gh version (\d+\.\d+\.\d+)/);
      ghVersion = ghMatch ? ghMatch[1] : null;
    } catch {
      // gh version check failed
    }

    // Get copilot extension version
    const copilotResult = await execFileAsync(ghPath, ['copilot', '--version'], {
      encoding: 'utf-8',
      timeout: 10000,
      windowsHide: true,
      env,
    });

    const output = copilotResult.stdout.trim();
    const match = output.match(/(\d+\.\d+\.\d+)/);
    const copilotVersion = match ? match[1] : null;

    return [!!copilotVersion, copilotVersion, ghVersion];
  } catch (error) {
    console.warn('[Copilot CLI] Validation failed:', error instanceof Error ? error.message : error);
    return [false, null, null];
  }
}

/**
 * Scan for all gh CLI installations that have the copilot extension
 */
async function scanCopilotInstallations(activePath: string | null): Promise<CopilotInstallationInfo[]> {
  const installations: CopilotInstallationInfo[] = [];
  const seenPaths = new Set<string>();

  const tryAddInstallation = async (
    ghPath: string,
    source: CopilotInstallationInfo['source']
  ): Promise<void> => {
    const normalizedPath = path.resolve(ghPath);
    if (seenPaths.has(normalizedPath.toLowerCase())) return;
    seenPaths.add(normalizedPath.toLowerCase());

    if (!existsSync(normalizedPath)) return;

    const [isValid, copilotVersion, ghVersion] = await validateCopilotCliAsync(normalizedPath);
    // Only add if copilot extension is installed (isValid)
    if (isValid) {
      installations.push({
        path: normalizedPath,
        version: copilotVersion,
        ghVersion,
        source,
        isActive: activePath ? normalizedPath === path.resolve(activePath) : false,
      });
    }
  };

  // 1. User-configured path
  const settings = readSettingsFile();
  if (settings?.copilotPath) {
    await tryAddInstallation(settings.copilotPath as string, 'user-config');
  }

  // 2. Currently detected gh path
  try {
    const ghInfo = getToolInfo('gh');
    if (ghInfo.found && ghInfo.path) {
      await tryAddInstallation(ghInfo.path, ghInfo.source);
    }
  } catch {
    // Detection failed
  }

  // 3. Common system paths
  const env = getAugmentedEnv();
  try {
    const whichCmd = isWindows() ? 'where' : 'which';
    const whichArgs = isWindows() ? ['gh'] : ['-a', 'gh'];
    const { stdout } = await execFileAsync(whichCmd, whichArgs, {
      encoding: 'utf-8',
      timeout: 5000,
      windowsHide: true,
      env,
    });
    const paths = stdout.trim().split('\n').map(p => p.trim()).filter(Boolean);
    for (const p of paths) {
      await tryAddInstallation(p, 'system-path');
    }
  } catch {
    // which/where failed
  }

  // Mark first as active if none is active
  if (installations.length > 0 && !installations.some(i => i.isActive)) {
    installations[0].isActive = true;
  }

  return installations;
}

/**
 * Fetch the latest copilot extension version from GitHub API (stable releases only)
 */
async function fetchLatestCopilotVersion(): Promise<string> {
  // Check cache
  if (cachedLatestCopilotVersion && Date.now() - cachedLatestCopilotVersion.timestamp < COPILOT_CACHE_DURATION_MS) {
    return cachedLatestCopilotVersion.version;
  }

  try {
    // Try using gh api if available - get all releases and filter for stable ones
    const ghPath = getToolPath('gh');
    const env = getAugmentedEnv();

    const { stdout } = await execFileAsync(ghPath, [
      'api', 'repos/github/copilot-cli/releases',
      '--jq', '[.[] | select(.prerelease == false) | .tag_name] | .[0]'
    ], {
      encoding: 'utf-8',
      timeout: 15000,
      windowsHide: true,
      env,
    });

    const version = stdout.trim().replace(/^v/, '').replace(/^"/, '').replace(/"$/, '');
    if (version && version !== 'null') {
      cachedLatestCopilotVersion = { version, timestamp: Date.now() };
      return version;
    }
  } catch (error) {
    console.warn('[Copilot CLI] Failed to fetch latest stable version via gh api:', error instanceof Error ? error.message : error);
  }

  // Fallback: fetch from GitHub API directly - get all releases and filter for stable ones
  try {
    const https = await import('https');
    const data = await new Promise<string>((resolve, reject) => {
      const req = https.get(
        'https://api.github.com/repos/github/copilot-cli/releases',
        {
          headers: {
            'User-Agent': 'Auto-Claude-EBP',
            'Accept': 'application/vnd.github.v3+json',
          },
          timeout: 10000,
        },
        (res) => {
          let body = '';
          res.on('data', (chunk: Buffer | string) => (body += chunk));
          res.on('end', () => resolve(body));
        }
      );
      req.on('error', reject);
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Request timed out'));
      });
    });

    const releases = JSON.parse(data);
    // Find the first non-prerelease release
    const stableRelease = releases.find((release: any) => !release.prerelease);
    const version = stableRelease ? (stableRelease.tag_name || '').replace(/^v/, '') : '';
    
    if (version) {
      cachedLatestCopilotVersion = { version, timestamp: Date.now() };
      return version;
    }
  } catch (error) {
    console.warn('[Copilot CLI] Failed to fetch latest stable version via HTTPS:', error instanceof Error ? error.message : error);
  }

  return 'unknown';
}

/**
 * Get the install command for Copilot CLI extension
 */
function getCopilotInstallCommand(isUpdate: boolean): string {
  if (isUpdate) {
    return 'gh extension upgrade gh-copilot';
  }
  return 'gh extension install github/gh-copilot';
}

/**
 * Open a terminal with the given command
 * Simplified version — delegates to the user's default terminal
 */
async function openTerminalWithCommand(command: string): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    try {
      if (isWindows()) {
        const cmdExe = process.env.ComSpec || 'cmd.exe';
        spawn(cmdExe, ['/c', 'start', 'cmd', '/k', command], {
          detached: true,
          stdio: 'ignore',
          windowsHide: false,
        }).unref();
      } else {
        // macOS / Linux — try common terminals
        const terminal = process.platform === 'darwin' ? 'open' : 'xterm';
        if (process.platform === 'darwin') {
          spawn('open', ['-a', 'Terminal.app', '--args', '-e', command], {
            detached: true,
            stdio: 'ignore',
          }).unref();
        } else {
          spawn(terminal, ['-e', command], {
            detached: true,
            stdio: 'ignore',
          }).unref();
        }
      }
      resolve();
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Check if the gh CLI is authenticated with Copilot
 */
async function checkCopilotAuth(ghPath: string): Promise<{ authenticated: boolean; username?: string; scopes?: string[] }> {
  try {
    const env = getAugmentedEnv();
    
    // First check GitHub CLI auth status
    const { stdout: authStatusOutput, stderr: authStatusStderr } = await execFileAsync(ghPath, ['auth', 'status'], {
      encoding: 'utf-8',
      timeout: 10000,
      windowsHide: true,
      env,
    });

    const authOutput = authStatusOutput.trim();
    const authError = authStatusStderr.trim();
    
    // Combine stdout and stderr for parsing (gh auth status outputs to both)
    const fullOutput = authOutput + '\n' + authError;
    
    // gh auth status shows "Logged in to github.com account USERNAME" on success
    const usernameMatch = fullOutput.match(/account\s+(\S+)/);
    const username = usernameMatch ? usernameMatch[1] : undefined;

    // Check if GitHub CLI is authenticated (look for ✓ or "Logged in" in the output)
    const isGitHubAuthed = fullOutput.includes('Logged in') || fullOutput.includes('✓');
    
    if (!isGitHubAuthed || !username) {
      return { authenticated: false };
    }

    // Now check if Copilot CLI is accessible and authenticated
    // Try to run a simple copilot command to verify authentication
    try {
      const { stdout: copilotVersionOutput } = await execFileAsync(ghPath, ['copilot', '--', 'version'], {
        encoding: 'utf-8',
        timeout: 15000,
        windowsHide: true,
        env,
      });

      // If we can get the version, Copilot CLI is working
      // Check if the version output indicates proper authentication
      const copilotOutput = copilotVersionOutput.trim();
      const hasVersion = copilotOutput.includes('GitHub Copilot CLI');
      
      if (hasVersion) {
        return {
          authenticated: true,
          username,
        };
      }
    } catch (copilotError) {
      // Copilot CLI command failed - likely not authenticated
      console.warn('[Copilot CLI] Copilot command failed:', copilotError instanceof Error ? copilotError.message : copilotError);
      return { authenticated: false, username };
    }

    return { authenticated: false, username };
  } catch (error) {
    // gh auth status exits with non-zero if not authenticated
    // but stderr may still contain useful info
    const stderr = (error as { stderr?: string }).stderr || '';
    const stdout = (error as { stdout?: string }).stdout || '';
    
    // Combine both outputs for parsing
    const fullOutput = stdout + '\n' + stderr;
    
    // Check if we can still find authentication info despite the error
    const usernameMatch = fullOutput.match(/account\s+(\S+)/);
    const username = usernameMatch ? usernameMatch[1] : undefined;
    
    const isGitHubAuthed = fullOutput.includes('Logged in') || fullOutput.includes('✓');
    
    if (isGitHubAuthed && username) {
      // GitHub CLI is authenticated despite the error (multiple accounts issue)
      // Now check Copilot CLI
      try {
        const env = getAugmentedEnv();
        const { stdout: copilotVersionOutput } = await execFileAsync(ghPath, ['copilot', '--', 'version'], {
          encoding: 'utf-8',
          timeout: 15000,
          windowsHide: true,
          env,
        });

        const copilotOutput = copilotVersionOutput.trim();
        const hasVersion = copilotOutput.includes('GitHub Copilot CLI');
        
        if (hasVersion) {
          return {
            authenticated: true,
            username,
          };
        }
      } catch (copilotError) {
        console.warn('[Copilot CLI] Copilot command failed:', copilotError instanceof Error ? copilotError.message : copilotError);
        return { authenticated: false, username };
      }
    }
    
    if (stderr.includes('not logged') || stderr.includes('no oauth token')) {
      return { authenticated: false };
    }
    console.warn('[Copilot CLI] Auth check error:', error instanceof Error ? error.message : error);
    return { authenticated: false };
  }
}

/**
 * Register Copilot CLI IPC handlers
 */
export function registerCopilotCliHandlers(): void {
  // Check Copilot CLI version
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_CLI_CHECK_VERSION,
    async (): Promise<IPCResult<CopilotCliVersionInfo>> => {
      try {
        console.warn('[Copilot CLI] Checking version...');

        // Get installed version via cli-tool-manager
        let detectionResult;
        try {
          detectionResult = getToolInfo('copilot');
          console.warn('[Copilot CLI] Detection result:', JSON.stringify(detectionResult, null, 2));
        } catch (detectionError) {
          console.error('[Copilot CLI] Detection error:', detectionError);
          throw new Error(`Detection failed: ${detectionError instanceof Error ? detectionError.message : 'Unknown error'}`);
        }

        const installed = detectionResult.found ? detectionResult.version || null : null;

        // Get gh version separately
        let ghVersion: string | null = null;
        try {
          const ghInfo = getToolInfo('gh');
          ghVersion = ghInfo.found ? ghInfo.version || null : null;
        } catch {
          // gh detection failed
        }

        // Fetch latest version from GitHub
        let latest: string;
        try {
          latest = await fetchLatestCopilotVersion();
        } catch {
          latest = 'unknown';
        }

        // Compare versions
        let isOutdated = false;
        if (installed && latest !== 'unknown') {
          try {
            const semver = await import('semver');
            const cleanInstalled = installed.replace(/^v/, '');
            const cleanLatest = latest.replace(/^v/, '');
            isOutdated = semver.default.lt(cleanInstalled, cleanLatest);
          } catch {
            isOutdated = false;
          }
        }

        console.warn('[Copilot CLI] Check complete:', { installed, ghVersion, latest, isOutdated });
        return {
          success: true,
          data: {
            installed,
            ghVersion,
            isOutdated,
            path: detectionResult.path,
            detectionResult,
          },
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot CLI] Check failed:', errorMsg, error);
        return {
          success: false,
          error: `Failed to check Copilot CLI version: ${errorMsg}`,
        };
      }
    }
  );

  // Install Copilot CLI extension (open terminal with install command)
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_CLI_INSTALL,
    async (): Promise<IPCResult<{ command: string }>> => {
      try {
        // Check if copilot is already installed to determine install vs upgrade
        let isUpdate = false;
        try {
          const detectionResult = getToolInfo('copilot');
          isUpdate = detectionResult.found && !!detectionResult.version;
        } catch {
          isUpdate = false;
        }

        const command = getCopilotInstallCommand(isUpdate);
        console.warn('[Copilot CLI] Install command:', command);
        await openTerminalWithCommand(command);

        return {
          success: true,
          data: { command },
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot CLI] Install failed:', errorMsg, error);
        return {
          success: false,
          error: `Failed to open terminal for installation: ${errorMsg}`,
        };
      }
    }
  );

  // Get all Copilot CLI installations found on the system
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_CLI_GET_INSTALLATIONS,
    async (): Promise<IPCResult<CopilotInstallationList>> => {
      try {
        console.log('[Copilot CLI] Scanning for installations...');

        const settings = readSettingsFile();
        const activePath = settings?.copilotPath as string | undefined;

        const installations = await scanCopilotInstallations(activePath || null);
        console.log('[Copilot CLI] Found', installations.length, 'installations');

        return {
          success: true,
          data: {
            installations,
            activePath: activePath || (installations.length > 0 ? installations[0].path : null),
          },
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot CLI] Failed to scan installations:', errorMsg, error);
        return {
          success: false,
          error: `Failed to scan Copilot CLI installations: ${errorMsg}`,
        };
      }
    }
  );

  // Set the active Copilot CLI (gh) path
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_CLI_SET_ACTIVE_PATH,
    async (_event, cliPath: string): Promise<IPCResult<{ path: string }>> => {
      try {
        console.log('[Copilot CLI] Setting active path:', cliPath);

        if (!isSecurePath(cliPath)) {
          throw new Error('Invalid path: contains potentially unsafe characters');
        }

        const normalizedPath = path.resolve(cliPath);

        if (!existsSync(normalizedPath)) {
          throw new Error('gh CLI not found at specified path');
        }

        const [isValid] = await validateCopilotCliAsync(normalizedPath);
        if (!isValid) {
          throw new Error('gh CLI at specified path does not have copilot extension or is not valid');
        }

        // Save to settings
        const currentSettings = readSettingsFile() || {};
        const mergedSettings = {
          ...DEFAULT_APP_SETTINGS,
          ...currentSettings,
          copilotPath: normalizedPath,
        } as Record<string, unknown>;
        writeSettingsFile(mergedSettings);

        // Update CLI tool manager cache
        configureTools({ copilotPath: normalizedPath });

        return {
          success: true,
          data: { path: normalizedPath },
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot CLI] Failed to set active path:', errorMsg, error);
        return {
          success: false,
          error: `Failed to set active Copilot CLI path: ${errorMsg}`,
        };
      }
    }
  );

  // Check Copilot CLI authentication status
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_CLI_CHECK_AUTH,
    async (): Promise<IPCResult<{ authenticated: boolean; username?: string }>> => {
      try {
        const ghPath = getToolPath('gh');
        const result = await checkCopilotAuth(ghPath);

        return {
          success: true,
          data: result,
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot CLI] Auth check failed:', errorMsg, error);
        return {
          success: false,
          error: `Failed to check Copilot CLI auth: ${errorMsg}`,
        };
      }
    }
  );

  // Start Copilot CLI authentication (open terminal with gh auth login)
  ipcMain.handle(
    IPC_CHANNELS.COPILOT_CLI_START_AUTH,
    async (): Promise<IPCResult<{ command: string }>> => {
      try {
        const command = 'gh auth login';
        console.warn('[Copilot CLI] Starting auth:', command);
        await openTerminalWithCommand(command);

        return {
          success: true,
          data: { command },
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Copilot CLI] Start auth failed:', errorMsg, error);
        return {
          success: false,
          error: `Failed to start Copilot CLI authentication: ${errorMsg}`,
        };
      }
    }
  );

  console.warn('[IPC] Copilot CLI handlers registered');
}
