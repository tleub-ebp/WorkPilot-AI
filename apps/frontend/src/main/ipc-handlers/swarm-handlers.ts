/**
 * Swarm Mode IPC Handlers
 *
 * Manages multi-agent parallel execution:
 * - Analyze subtask dependencies from implementation plan
 * - Start swarm execution with configurable parallelism
 * - Stream wave/subtask events to renderer
 * - Cancel running swarms
 */

import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import * as path from 'node:path';
import { spawn } from 'node:child_process';
import type { ChildProcess } from 'node:child_process';
import { appLog } from '../app-logger';
import type { SwarmConfig } from '../../shared/types/swarm';

// ─── Constants ───────────────────────────────────────────────────────────────

const SWARM_EVENT_PREFIX = '__SWARM_EVENT__:';
const EXEC_PHASE_PREFIX = '__EXEC_PHASE__:';

// ─── Active process tracking ─────────────────────────────────────────────────

let activeSwarmProcess: ChildProcess | null = null;
let activeSwarmProjectId: string | null = null;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function parseSwarmEvent(line: string): Record<string, unknown> | null {
  const idx = line.indexOf(SWARM_EVENT_PREFIX);
  if (idx === -1) return null;
  const json = line.slice(idx + SWARM_EVENT_PREFIX.length);
  try {
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function killSwarmProcess(): void {
  if (activeSwarmProcess) {
    try {
      activeSwarmProcess.kill('SIGTERM');
      // Give it 5s then force kill
      setTimeout(() => {
        if (activeSwarmProcess && !activeSwarmProcess.killed) {
          activeSwarmProcess.kill('SIGKILL');
        }
      }, 5000);
    } catch {
      // already dead
    }
    activeSwarmProcess = null;
    activeSwarmProjectId = null;
  }
}

// ─── Registration ────────────────────────────────────────────────────────────

export function registerSwarmHandlers(
  getPythonPath: () => string,
  getAutoBuildSourcePath: () => string,
  getMainWindow: () => BrowserWindow | null,
): void {
  /**
   * Analyze dependencies without executing.
   * Returns parallelism stats and wave plan.
   */
  ipcMain.handle(
    'swarm:analyze',
    async (_event, specId: string, config: SwarmConfig) => {
      try {
        appLog.info(`[Swarm] Analyzing dependencies for spec: ${specId}`);

        const pythonPath = getPythonPath();
        const sourcePath = getAutoBuildSourcePath();
        const runnerPath = path.join(sourcePath, 'runners', 'swarm_runner.py');

        return await new Promise<Record<string, unknown>>((resolve, reject) => {
          const args = [
            runnerPath,
            '--spec', specId,
            '--analyze-only',
            '--max-parallel', String(config.maxParallelAgents),
          ];

          const proc = spawn(pythonPath, args, {
            env: { ...process.env, PYTHONPATH: sourcePath },
          });

          let stdout = '';
          let stderr = '';

          proc.stdout?.on('data', (data: Buffer) => {
            stdout += data.toString();
          });

          proc.stderr?.on('data', (data: Buffer) => {
            stderr += data.toString();
          });

          proc.on('close', (code) => {
            if (code !== 0) {
              reject(new Error(stderr || `Analysis failed with code ${code}`));
              return;
            }

            // Parse the last SWARM_EVENT with analysis_complete type
            const lines = stdout.split('\n');
            for (let i = lines.length - 1; i >= 0; i--) {
              const event = parseSwarmEvent(lines[i]);
              if (event && event.type === 'analysis_complete') {
                resolve(event);
                return;
              }
            }

            reject(new Error('No analysis result found in output'));
          });

          proc.on('error', (err) => {
            reject(new Error(`Failed to spawn analysis: ${err.message}`));
          });
        });
      } catch (err) {
        appLog.error(`[Swarm] Analysis failed: ${err}`);
        return {
          success: false,
          error: err instanceof Error ? err.message : 'Unknown error',
        };
      }
    },
  );

  /**
   * Start swarm execution.
   * Streams events to the renderer via webContents.send().
   */
  ipcMain.handle(
    'swarm:start',
    async (_event, specId: string, config: SwarmConfig, projectId?: string) => {
      try {
        // Kill any existing swarm process
        killSwarmProcess();

        appLog.info(
          `[Swarm] Starting execution for spec: ${specId} (max parallel: ${config.maxParallelAgents})`,
        );

        const pythonPath = getPythonPath();
        const sourcePath = getAutoBuildSourcePath();
        const runnerPath = path.join(sourcePath, 'runners', 'swarm_runner.py');

        const args = [
          runnerPath,
          '--spec', specId,
          '--max-parallel', String(config.maxParallelAgents),
        ];

        if (config.failFast) args.push('--fail-fast');
        if (!config.mergeAfterEachWave) args.push('--no-merge');
        if (config.dryRun) args.push('--dry-run');

        const proc = spawn(pythonPath, args, {
          env: { ...process.env, PYTHONPATH: sourcePath },
        });

        activeSwarmProcess = proc;
        activeSwarmProjectId = projectId ?? null;

        const win = getMainWindow();

        // Stream stdout events to renderer
        let lineBuffer = '';
        proc.stdout?.on('data', (data: Buffer) => {
          lineBuffer += data.toString();
          const lines = lineBuffer.split('\n');
          lineBuffer = lines.pop() ?? ''; // keep incomplete last line

          for (const line of lines) {
            // Parse swarm events
            const event = parseSwarmEvent(line);
            if (event) {
              if (win && !win.isDestroyed()) {
                win.webContents.send('swarm:event', event);
              }
              continue;
            }

            // Forward exec phase events
            if (line.includes(EXEC_PHASE_PREFIX)) {
              if (win && !win.isDestroyed()) {
                win.webContents.send('swarm:log', line);
              }
            }
          }
        });

        proc.stderr?.on('data', (data: Buffer) => {
          const text = data.toString();
          appLog.warn(`[Swarm] stderr: ${text.slice(0, 500)}`);
        });

        proc.on('close', (code) => {
          appLog.info(`[Swarm] Process exited with code ${code}`);
          activeSwarmProcess = null;
          activeSwarmProjectId = null;

          if (win && !win.isDestroyed()) {
            win.webContents.send('swarm:event', {
              type: code === 0 ? 'swarm_complete' : 'swarm_failed',
              exitCode: code,
              error: code !== 0 ? `Process exited with code ${code}` : undefined,
            });
          }
        });

        proc.on('error', (err) => {
          appLog.error(`[Swarm] Process error: ${err.message}`);
          activeSwarmProcess = null;
          activeSwarmProjectId = null;

          if (win && !win.isDestroyed()) {
            win.webContents.send('swarm:event', {
              type: 'swarm_failed',
              error: err.message,
            });
          }
        });

        return { success: true, pid: proc.pid };
      } catch (err) {
        appLog.error(`[Swarm] Failed to start: ${err}`);
        return {
          success: false,
          error: err instanceof Error ? err.message : 'Unknown error',
        };
      }
    },
  );

  /**
   * Cancel the running swarm.
   */
  ipcMain.handle('swarm:cancel', async () => {
    if (!activeSwarmProcess) {
      return { success: false, error: 'No active swarm process' };
    }

    appLog.info('[Swarm] Cancelling execution');
    killSwarmProcess();
    return { success: true };
  });

  /**
   * Get swarm status.
   */
  ipcMain.handle('swarm:status', async () => {
    return {
      isRunning: activeSwarmProcess !== null,
      projectId: activeSwarmProjectId,
      pid: activeSwarmProcess?.pid ?? null,
    };
  });
}
