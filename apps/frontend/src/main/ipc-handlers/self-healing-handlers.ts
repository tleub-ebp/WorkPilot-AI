/**
 * Self-Healing Codebase + Incident Responder IPC Handlers
 *
 * Feature #3 (Tier S+) - Handles communication between the renderer
 * and the backend self-healing system.
 */

import { ipcMain, type BrowserWindow } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import path from 'node:path';
import { spawn, type ChildProcess } from 'node:child_process';

/** Tracks running fix/retry processes by incident ID so they can be cancelled. */
const activeFixProcesses = new Map<string, ChildProcess>();

/**
 * Register all self-healing IPC handlers.
 */
export function registerSelfHealingHandlers(
  getMainWindow: () => BrowserWindow | null
): void {
  // ── Dashboard data ────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_GET_DASHBOARD, async (_, projectPath: string) => {
    try {
      const result = await runSelfHealingCommand(projectPath, ['dashboard', '--json']);
      return { success: true, data: JSON.parse(result) };
    } catch {
      return { success: true, data: getEmptyDashboard() };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_GET_INCIDENTS, async (_, projectPath: string, mode?: string) => {
    try {
      const args = ['incidents'];
      if (mode) args.push('--mode', mode);
      const result = await runSelfHealingCommand(projectPath, args);
      return { success: true, data: JSON.parse(result) };
    } catch {
      return { success: true, data: [] };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_GET_OPERATIONS, async (_, projectPath: string) => {
    try {
      const result = await runSelfHealingCommand(projectPath, ['operations']);
      return { success: true, data: JSON.parse(result) };
    } catch {
      return { success: true, data: [] };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_GET_FRAGILITY, async (_, projectPath: string) => {
    try {
      const result = await runSelfHealingCommand(projectPath, ['proactive', '--json']);
      return { success: true, data: JSON.parse(result) };
    } catch {
      return { success: true, data: [] };
    }
  });

  // ── CI/CD Mode ────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_CICD_ENABLE, async (_, projectPath: string) => {
    try {
      const result = await runSelfHealingCommand(projectPath, [
        'config', '--mode', 'cicd', '--data', JSON.stringify({ enabled: true }),
      ]);
      return JSON.parse(result);
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_CICD_DISABLE, async (_, projectPath: string) => {
    try {
      const result = await runSelfHealingCommand(projectPath, [
        'config', '--mode', 'cicd', '--data', JSON.stringify({ enabled: false }),
      ]);
      return JSON.parse(result);
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_CICD_CONFIG, async (_, projectPath: string, config: Record<string, unknown>) => {
    try {
      const result = await runSelfHealingCommand(projectPath, [
        'config', '--mode', 'cicd', '--data', JSON.stringify(config),
      ]);
      return JSON.parse(result);
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  // ── Production Mode ───────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_PRODUCTION_CONNECT, async (_, projectPath: string, sourceConfig: Record<string, unknown>) => {
    try {
      const source = typeof sourceConfig.source === 'string' ? sourceConfig.source : '';
      const result = await runSelfHealingCommand(projectPath, [
        'connect', '--source', source, '--config', JSON.stringify(sourceConfig),
      ]);
      return JSON.parse(result);
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_PRODUCTION_DISCONNECT, async (_, projectPath: string, source: string) => {
    try {
      const result = await runSelfHealingCommand(projectPath, [
        'disconnect', '--source', source,
      ]);
      return JSON.parse(result);
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_PRODUCTION_CONFIG, async (_, projectPath: string, config: Record<string, unknown>) => {
    try {
      const result = await runSelfHealingCommand(projectPath, [
        'config', '--mode', 'production', '--data', JSON.stringify(config),
      ]);
      return JSON.parse(result);
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  // ── Proactive Mode ────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_PROACTIVE_SCAN, async (_, projectPath: string) => {
    const mainWindow = getMainWindow();
    try {
      await runSelfHealingCommand(projectPath, ['proactive']);
      mainWindow?.webContents.send(IPC_CHANNELS.SELF_HEALING_OPERATION_COMPLETE, {
        mode: 'proactive',
        success: true,
      });
      return { success: true };
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_PROACTIVE_CONFIG, async (_, projectPath: string, config: Record<string, unknown>) => {
    try {
      const result = await runSelfHealingCommand(projectPath, [
        'config', '--mode', 'proactive', '--data', JSON.stringify(config),
      ]);
      return JSON.parse(result);
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  // ── Actions ───────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_TRIGGER_FIX, async (_, projectPath: string, incidentId: string) => {
    const mainWindow = getMainWindow();
    try {
      await runSelfHealingCommandStreaming(
        projectPath,
        ['fix', '--incident-id', incidentId],
        (progress) => {
          mainWindow?.webContents.send(IPC_CHANNELS.SELF_HEALING_OPERATION_PROGRESS, {
            incidentId,
            ...progress,
          });
        },
        incidentId,
      );
      mainWindow?.webContents.send(IPC_CHANNELS.SELF_HEALING_OPERATION_COMPLETE, {
        incidentId,
        success: true,
      });
      return { success: true };
    } catch (error) {
      mainWindow?.webContents.send(IPC_CHANNELS.SELF_HEALING_OPERATION_COMPLETE, {
        incidentId,
        success: false,
        error: String(error),
      });
      return { success: false, error: String(error) };
    } finally {
      activeFixProcesses.delete(incidentId);
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_CANCEL_OPERATION, async (_, projectPath: string, operationId: string) => {
    // Kill any running fix process associated with this operation
    // The operationId may be prefixed with the incidentId — try both
    for (const [key, proc] of activeFixProcesses.entries()) {
      if (key === operationId || operationId.includes(key)) {
        proc.kill('SIGTERM');
        activeFixProcesses.delete(key);
        break;
      }
    }
    // Also persist the cancelled state in JSON via the backend
    try {
      const result = await runSelfHealingCommand(projectPath, [
        'cancel', '--operation-id', operationId,
      ]);
      return JSON.parse(result);
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_DISMISS_INCIDENT, async (_, projectPath: string, incidentId: string) => {
    try {
      const result = await runSelfHealingCommand(projectPath, [
        'dismiss', '--incident-id', incidentId,
      ]);
      return JSON.parse(result);
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_RETRY_INCIDENT, async (_, projectPath: string, incidentId: string) => {
    const mainWindow = getMainWindow();
    try {
      await runSelfHealingCommandStreaming(
        projectPath,
        ['retry', '--incident-id', incidentId],
        (progress) => {
          mainWindow?.webContents.send(IPC_CHANNELS.SELF_HEALING_OPERATION_PROGRESS, {
            incidentId,
            ...progress,
          });
        },
        incidentId,
      );
      mainWindow?.webContents.send(IPC_CHANNELS.SELF_HEALING_OPERATION_COMPLETE, {
        incidentId,
        success: true,
      });
      return { success: true };
    } catch (error) {
      return { success: false, error: String(error) };
    } finally {
      activeFixProcesses.delete(incidentId);
    }
  });
}

// ── Helpers ───────────────────────────────────────────────────

function getEmptyDashboard() {
  return {
    incidents: [],
    activeOperations: [],
    fragilityReports: [],
    stats: {
      totalIncidents: 0,
      resolvedIncidents: 0,
      activeIncidents: 0,
      avgResolutionTime: 0,
      autoFixRate: 0,
    },
    productionStatus: {
      connected_sources: [],
      configs: {},
    },
    proactiveSummary: {
      scanned: false,
      files_at_risk: 0,
      avg_risk: 0,
      max_risk: 0,
      top_files: [],
    },
  };
}

function getRunnerPath(): string {
  return path.join(__dirname, '..', '..', '..', '..', 'backend', 'runners', 'self_healing_runner.py');
}

function runSelfHealingCommand(projectPath: string, args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn('python', [getRunnerPath(), '--project', projectPath, ...args], {
      cwd: projectPath,
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 120000,
    });

    let stdout = '';
    let stderr = '';

    proc.stdout?.on('data', (data: Buffer) => { stdout += data.toString(); });
    proc.stderr?.on('data', (data: Buffer) => { stderr += data.toString(); });

    proc.on('close', (code: number | null) => {
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(`Self-healing runner exited with code ${code}: ${stderr}`));
      }
    });

    proc.on('error', (err: Error) => { reject(err); });
  });
}

/**
 * Spawns a self-healing command and emits progress events for each JSON line
 * printed to stdout. Registers the process in `activeFixProcesses` under `trackKey`
 * so it can be killed by the cancel handler.
 */
function runSelfHealingCommandStreaming(
  projectPath: string,
  args: string[],
  onProgress: (data: Record<string, unknown>) => void,
  trackKey: string,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn('python', [getRunnerPath(), '--project', projectPath, ...args], {
      cwd: projectPath,
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 300000,
    });

    activeFixProcesses.set(trackKey, proc);

    let stdout = '';
    let stderr = '';
    let lineBuffer = '';

    proc.stdout?.on('data', (data: Buffer) => {
      const chunk = data.toString();
      stdout += chunk;
      lineBuffer += chunk;

      const lines = lineBuffer.split('\n');
      lineBuffer = lines.pop() ?? '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          onProgress(JSON.parse(trimmed) as Record<string, unknown>);
        } catch {
          // Non-JSON output (e.g. print statements) — ignore
        }
      }
    });

    proc.stderr?.on('data', (data: Buffer) => { stderr += data.toString(); });

    proc.on('close', (code: number | null) => {
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(`Self-healing runner exited with code ${code}: ${stderr}`));
      }
    });

    proc.on('error', (err: Error) => { reject(err); });
  });
}
