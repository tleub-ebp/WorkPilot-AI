/**
 * Self-Healing Codebase + Incident Responder IPC Handlers
 *
 * Feature #3 (Tier S+) - Handles communication between the renderer
 * and the backend self-healing system.
 */

import { ipcMain, type BrowserWindow } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import path from 'node:path';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { spawn, type ChildProcess } from 'node:child_process';
import { getConfiguredPythonPath } from '../python-env-manager';

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
    let dashboard: Record<string, unknown>;
    try {
      const result = await runSelfHealingCommand(projectPath, ['dashboard', '--json']);
      dashboard = JSON.parse(result);
    } catch {
      dashboard = await getEmptyDashboardWithPersistedData(projectPath);
    }

    // Always read persisted config so the UI restores toggle states
    // (even when the Python dashboard command fails)
    const config = await readConfig(projectPath);
    dashboard.cicdConfig = config.cicd || null;
    dashboard.productionConfig = config.production || null;
    dashboard.proactiveConfig = config.proactive || null;

    return { success: true, data: dashboard };
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
    // Try Python backend first, then fall back to reading persisted file
    try {
      const result = await runSelfHealingCommand(projectPath, ['proactive', '--json']);
      return { success: true, data: JSON.parse(result) };
    } catch {
      // Read from persisted file (written by scan)
      try {
        const filePath = path.join(projectPath, '.workpilot', 'self-healing', 'fragility_reports.json');
        const raw = await readFile(filePath, 'utf-8');
        return { success: true, data: JSON.parse(raw) };
      } catch {
        return { success: true, data: [] };
      }
    }
  });

  // ── CI/CD Mode ────────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_CICD_ENABLE, async (_, projectPath: string) => {
    try {
      const config = await updateModeConfig(projectPath, 'cicd', { enabled: true });
      return { success: true, mode: 'cicd', config };
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_CICD_DISABLE, async (_, projectPath: string) => {
    try {
      const config = await updateModeConfig(projectPath, 'cicd', { enabled: false });
      return { success: true, mode: 'cicd', config };
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_CICD_CONFIG, async (_, projectPath: string, config: Record<string, unknown>) => {
    try {
      const merged = await updateModeConfig(projectPath, 'cicd', config);
      return { success: true, mode: 'cicd', config: merged };
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
      const merged = await updateModeConfig(projectPath, 'production', config);
      return { success: true, mode: 'production', config: merged };
    } catch (error) {
      return { success: false, error: String(error) };
    }
  });

  // ── Proactive Mode ────────────────────────────────────────

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_PROACTIVE_SCAN, async (_, projectPath: string) => {
    const mainWindow = getMainWindow();

    // Try Python backend first; fall back to built-in Node.js scanner
    try {
      await runSelfHealingCommand(projectPath, ['proactive']);
    } catch {
      // Python backend unavailable — run lightweight Node.js scanner
      try {
        const reports = await runBuiltinFragilityScan(projectPath);
        // Persist results so the dashboard can read them
        const dataDir = path.join(projectPath, '.workpilot', 'self-healing');
        await mkdir(dataDir, { recursive: true });
        await writeFile(
          path.join(dataDir, 'fragility_reports.json'),
          JSON.stringify(reports, null, 2),
          'utf-8',
        );
      } catch (scanErr) {
        return { success: false, error: String(scanErr) };
      }
    }

    mainWindow?.webContents.send(IPC_CHANNELS.SELF_HEALING_OPERATION_COMPLETE, {
      mode: 'proactive',
      success: true,
    });
    return { success: true };
  });

  ipcMain.handle(IPC_CHANNELS.SELF_HEALING_PROACTIVE_CONFIG, async (_, projectPath: string, config: Record<string, unknown>) => {
    try {
      const merged = await updateModeConfig(projectPath, 'proactive', config);
      return { success: true, mode: 'proactive', config: merged };
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

// ── Built-in fragility scanner (Node.js — no Python dependency) ──

interface FragilityReportData {
  file_path: string;
  risk_score: number;
  cyclomatic_complexity: number;
  git_churn_count: number;
  test_coverage_percent: number;
  suggested_tests: string[];
}

const SOURCE_EXTENSIONS = ['.ts', '.tsx', '.js', '.jsx', '.py', '.java', '.go', '.rs', '.cs', '.rb'];
const EXCLUDED_PATTERNS = ['node_modules', '.test.', '.spec.', '__tests__', 'dist/', 'build/'];
const BRANCH_KEYWORDS = /\b(if|else|for|while|switch|case|catch|&&|\|\||\?)\b/g;

function isSourceFile(filePath: string): boolean {
  return (
    SOURCE_EXTENSIONS.some((ext) => filePath.endsWith(ext)) &&
    !EXCLUDED_PATTERNS.some((pat) => filePath.includes(pat))
  );
}

async function getGitChurnMap(projectPath: string): Promise<Map<string, number>> {
  const churnMap = new Map<string, number>();
  try {
    const output = await runShellCommand(
      projectPath,
      'git log --since="90 days ago" --name-only --pretty=format:""',
    );
    for (const line of output.split('\n')) {
      const trimmed = line.trim();
      if (trimmed) churnMap.set(trimmed, (churnMap.get(trimmed) || 0) + 1);
    }
  } catch {
    // Not a git repo or git unavailable
  }
  return churnMap;
}

async function getTrackedSourceFiles(projectPath: string): Promise<string[]> {
  const output = await runShellCommand(projectPath, 'git ls-files');
  return output.split('\n').map((l) => l.trim()).filter((l) => l && isSourceFile(l));
}

function computeComplexity(content: string): number {
  let complexity = 1;
  for (const line of content.split('\n')) {
    const matches = line.match(BRANCH_KEYWORDS);
    if (matches) complexity += matches.length;
  }
  return complexity;
}

function computeRiskScore(complexity: number, churn: number, lineCount: number): number {
  const complexityScore = Math.min(100, (complexity / 50) * 100);
  const churnScore = Math.min(100, (churn / 20) * 100);
  const sizeScore = Math.min(100, (lineCount / 500) * 100);
  return complexityScore * 0.4 + churnScore * 0.4 + sizeScore * 0.2;
}

async function analyseFile(
  projectPath: string,
  filePath: string,
  churnMap: Map<string, number>,
): Promise<FragilityReportData | null> {
  try {
    const content = await readFile(path.join(projectPath, filePath), 'utf-8');
    const lineCount = Math.max(content.split('\n').length, 1);
    const complexity = computeComplexity(content);
    const churn = churnMap.get(filePath) || 0;
    const riskScore = computeRiskScore(complexity, churn, lineCount);

    return {
      file_path: filePath,
      risk_score: Math.round(riskScore * 10) / 10,
      cyclomatic_complexity: complexity,
      git_churn_count: churn,
      test_coverage_percent: 0,
      suggested_tests: [],
    };
  } catch {
    return null;
  }
}

/**
 * Lightweight fragility scanner that runs entirely in Node.js.
 * Analyses source files for complexity (branch keywords) and git churn.
 */
async function runBuiltinFragilityScan(projectPath: string): Promise<FragilityReportData[]> {
  const churnMap = await getGitChurnMap(projectPath);

  let sourceFiles: string[];
  try {
    sourceFiles = await getTrackedSourceFiles(projectPath);
  } catch {
    return [];
  }

  const config = await readConfig(projectPath);
  const threshold = Number(config.proactive?.riskThreshold ?? 40);

  const results = await Promise.all(
    sourceFiles.map((f) => analyseFile(projectPath, f, churnMap)),
  );

  return results
    .filter((r): r is FragilityReportData => r !== null && r.risk_score >= threshold)
    .sort((a, b) => b.risk_score - a.risk_score)
    .slice(0, 30);
}

function runShellCommand(cwd: string, command: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn(command, {
      cwd,
      shell: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 30000,
    });
    let stdout = '';
    proc.stdout?.on('data', (data: Buffer) => { stdout += data.toString(); });
    proc.on('close', (code: number | null) => {
      if (code === 0) resolve(stdout);
      else reject(new Error(`Command failed with code ${code}`));
    });
    proc.on('error', reject);
  });
}

// ── Config helpers (Node.js fs — no Python dependency) ────────

function getConfigPath(projectPath: string): string {
  return path.join(projectPath, '.workpilot', 'self-healing', 'config.json');
}

async function readConfig(projectPath: string): Promise<Record<string, Record<string, unknown>>> {
  try {
    const raw = await readFile(getConfigPath(projectPath), 'utf-8');
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

async function writeConfig(projectPath: string, config: Record<string, unknown>): Promise<void> {
  const configPath = getConfigPath(projectPath);
  await mkdir(path.dirname(configPath), { recursive: true });
  await writeFile(configPath, JSON.stringify(config, null, 2), 'utf-8');
}

async function updateModeConfig(
  projectPath: string,
  mode: string,
  newConfig: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const existing = await readConfig(projectPath);
  const merged = { ...(existing[mode]), ...newConfig };
  existing[mode] = merged;
  await writeConfig(projectPath, existing);
  return merged;
}

// ── Helpers ───────────────────────────────────────────────────

async function readJsonFile(filePath: string): Promise<unknown[]> {
  try {
    const raw = await readFile(filePath, 'utf-8');
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

async function getEmptyDashboardWithPersistedData(projectPath: string) {
  const dataDir = path.join(projectPath, '.workpilot', 'self-healing');
  const incidents = await readJsonFile(path.join(dataDir, 'incidents.json')) as Record<string, unknown>[];
  const operations = await readJsonFile(path.join(dataDir, 'operations.json')) as Record<string, unknown>[];
  const fragilityReports = await readJsonFile(path.join(dataDir, 'fragility_reports.json'));

  const resolved = incidents.filter((i) => i.status === 'resolved').length;
  const active = incidents.filter((i) => i.status !== 'resolved' && i.status !== 'failed').length;

  return {
    incidents,
    activeOperations: operations.filter((o) => !o.completed_at),
    fragilityReports,
    stats: {
      totalIncidents: incidents.length,
      resolvedIncidents: resolved,
      activeIncidents: active,
      avgResolutionTime: 0,
      autoFixRate: incidents.length > 0 ? Math.round((resolved / incidents.length) * 100) : 0,
    },
    productionStatus: { connected_sources: [], configs: {} },
    proactiveSummary: { scanned: fragilityReports.length > 0, files_at_risk: fragilityReports.length, avg_risk: 0, max_risk: 0, top_files: [] },
  };
}

function getBackendDir(): string {
  // In packaged app: resources/backend | In dev: apps/backend
  const devPath = path.resolve(__dirname, '..', '..', '..', '..', 'apps', 'backend');
  const resourcesPath = path.resolve(process.resourcesPath || '', 'backend');
  return existsSync(resourcesPath) ? resourcesPath : devPath;
}

function getRunnerPath(): string {
  return path.join(getBackendDir(), 'runners', 'self_healing_runner.py');
}

function runSelfHealingCommand(projectPath: string, args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const backendDir = getBackendDir();
    const pythonPath = getConfiguredPythonPath() || 'python3';
    const proc = spawn(pythonPath, [getRunnerPath(), '--project', projectPath, ...args], {
      cwd: backendDir,
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 120000,
      env: {
        ...process.env,
        PYTHONPATH: backendDir,
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1',
      },
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
    const backendDir = getBackendDir();
    const pythonPath = getConfiguredPythonPath() || 'python3';
    const proc = spawn(pythonPath, [getRunnerPath(), '--project', projectPath, ...args], {
      cwd: backendDir,
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 300000,
      env: {
        ...process.env,
        PYTHONPATH: backendDir,
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1',
      },
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
