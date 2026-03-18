/**
 * CI/CD Deployment Triggers IPC Handlers (Feature 44)
 *
 * Exposes channels for triggering deployment pipelines after agent PRs:
 *   cicdTriggers:getConfig      — Current trigger configuration per provider
 *   cicdTriggers:setConfig      — Update trigger configuration
 *   cicdTriggers:listRuns       — Recent pipeline run history
 *   cicdTriggers:trigger        — Manually trigger a pipeline for a PR
 *   cicdTriggers:getRunStatus   — Get status of a specific pipeline run
 *   cicdTriggers:cancelRun      — Cancel a running pipeline
 *
 * Supported providers: GitHub Actions, GitLab CI, Azure DevOps Pipelines, Jenkins
 */

import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { spawn } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { getConfiguredPythonPath } from '../python-env-manager';
import { parsePythonCommand } from '../python-detector';

function getRunnerPath(): string {
  return path.join(
    __dirname, '..', '..', '..', '..', '..', 'apps', 'backend', 'runners', 'cicd_triggers_runner.py',
  );
}

async function runRunner(
  projectDir: string,
  args: string[],
): Promise<{ success: boolean; data?: unknown; error?: string }> {
  const pythonPath = await getConfiguredPythonPath(projectDir);
  const { cmd, cmdArgs } = parsePythonCommand(pythonPath, [getRunnerPath(), ...args]);

  return new Promise((resolve) => {
    const env = { ...process.env } as Record<string, string>;
    const envFilePath = path.join(projectDir, '.env');
    if (fs.existsSync(envFilePath)) {
      try {
        for (const line of fs.readFileSync(envFilePath, 'utf-8').split('\n')) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('#')) continue;
          const eqIdx = trimmed.indexOf('=');
          if (eqIdx < 0) continue;
          env[trimmed.slice(0, eqIdx).trim()] = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
        }
      } catch { /* ignore */ }
    }

    const proc = spawn(cmd, cmdArgs, { env, cwd: projectDir });
    const stdout: string[] = [];
    const stderr: string[] = [];
    proc.stdout?.on('data', (d: Buffer) => stdout.push(d.toString()));
    proc.stderr?.on('data', (d: Buffer) => stderr.push(d.toString()));

    proc.on('close', (code) => {
      const out = stdout.join('').trim();
      if (code === 0) {
        try { resolve({ success: true, data: JSON.parse(out) }); }
        catch { resolve({ success: true, data: { message: out } }); }
      } else {
        resolve({ success: false, error: stderr.join('').trim() || out });
      }
    });
    proc.on('error', (err) => resolve({ success: false, error: err.message }));
  });
}

function readCicdConfig(projectDir: string): Record<string, string> {
  const envPath = path.join(projectDir, '.env');
  const result: Record<string, string> = {};
  if (!fs.existsSync(envPath)) return result;
  try {
    for (const line of fs.readFileSync(envPath, 'utf-8').split('\n')) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('CICD_')) continue;
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx < 0) continue;
      result[trimmed.slice(0, eqIdx).trim()] = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
    }
  } catch { /* ignore */ }
  return result;
}

function writeCicdConfig(projectDir: string, config: Record<string, string>): void {
  const envPath = path.join(projectDir, '.env');
  let content = '';
  try { content = fs.existsSync(envPath) ? fs.readFileSync(envPath, 'utf-8') : ''; }
  catch { content = ''; }
  for (const [key, value] of Object.entries(config)) {
    const regex = new RegExp(`^${key}=.*$`, 'm');
    const line = `${key}=${value}`;
    if (regex.test(content)) { content = content.replace(regex, line); }
    else { content = content.trimEnd() + '\n' + line + '\n'; }
  }
  fs.mkdirSync(path.dirname(envPath), { recursive: true });
  fs.writeFileSync(envPath, content, 'utf-8');
}

function getRunsLogPath(projectDir: string): string {
  return path.join(projectDir, '.auto-claude', 'cicd_runs.json');
}

function loadRuns(projectDir: string): object[] {
  const logPath = getRunsLogPath(projectDir);
  if (!fs.existsSync(logPath)) return [];
  try { return JSON.parse(fs.readFileSync(logPath, 'utf-8')); }
  catch { return []; }
}

function saveRun(projectDir: string, run: object): void {
  const runs = loadRuns(projectDir);
  runs.unshift(run);
  // Keep last 200 runs
  const trimmed = runs.slice(0, 200);
  fs.mkdirSync(path.dirname(getRunsLogPath(projectDir)), { recursive: true });
  fs.writeFileSync(getRunsLogPath(projectDir), JSON.stringify(trimmed, null, 2), 'utf-8');
}

export function registerCICDTriggersHandlers(): void {
  ipcMain.handle('cicdTriggers:getConfig', (_event, projectDir: string) => {
    try {
      const cfg = readCicdConfig(projectDir);
      return {
        success: true,
        data: {
          provider: cfg['CICD_PROVIDER'] ?? '',
          enabled: cfg['CICD_AUTO_TRIGGER'] === 'true',
          trigger_on_pr: cfg['CICD_TRIGGER_ON_PR'] !== 'false',
          trigger_on_merge: cfg['CICD_TRIGGER_ON_MERGE'] !== 'false',
          // GitHub Actions
          github_token: cfg['CICD_GITHUB_TOKEN'] ? '***' : '',
          github_workflow: cfg['CICD_GITHUB_WORKFLOW'] ?? '',
          github_ref: cfg['CICD_GITHUB_REF'] ?? 'main',
          // GitLab CI
          gitlab_token: cfg['CICD_GITLAB_TOKEN'] ? '***' : '',
          gitlab_project_id: cfg['CICD_GITLAB_PROJECT_ID'] ?? '',
          gitlab_ref: cfg['CICD_GITLAB_REF'] ?? 'main',
          // Azure DevOps
          azure_token: cfg['CICD_AZURE_TOKEN'] ? '***' : '',
          azure_org: cfg['CICD_AZURE_ORG'] ?? '',
          azure_project: cfg['CICD_AZURE_PROJECT'] ?? '',
          azure_pipeline_id: cfg['CICD_AZURE_PIPELINE_ID'] ?? '',
          // Jenkins
          jenkins_url: cfg['CICD_JENKINS_URL'] ?? '',
          jenkins_token: cfg['CICD_JENKINS_TOKEN'] ? '***' : '',
          jenkins_job: cfg['CICD_JENKINS_JOB'] ?? '',
        },
      };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle('cicdTriggers:setConfig', (_event, projectDir: string, config: Record<string, string>) => {
    try {
      const envConfig: Record<string, string> = {};
      for (const [key, value] of Object.entries(config)) {
        envConfig[`CICD_${key.toUpperCase()}`] = String(value);
      }
      writeCicdConfig(projectDir, envConfig);
      return { success: true };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle('cicdTriggers:listRuns', (_event, projectDir: string, limit: number = 50) => {
    try {
      const runs = loadRuns(projectDir).slice(0, limit);
      return { success: true, data: runs };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle('cicdTriggers:trigger', async (_event, projectDir: string, params: {
    provider: string;
    pr_url?: string;
    branch?: string;
    workflow?: string;
    ref?: string;
  }) => {
    const run = {
      id: Date.now().toString(),
      triggered_at: new Date().toISOString(),
      status: 'pending',
      provider: params.provider,
      pr_url: params.pr_url ?? '',
      branch: params.branch ?? '',
    };
    saveRun(projectDir, run);

    const result = await runRunner(projectDir, [
      '--action', 'trigger',
      '--provider', params.provider,
      '--project', projectDir,
      ...(params.pr_url ? ['--pr-url', params.pr_url] : []),
      ...(params.branch ? ['--branch', params.branch] : []),
      ...(params.workflow ? ['--workflow', params.workflow] : []),
      '--output-json',
    ]);

    // Update run status
    const runs = loadRuns(projectDir);
    const idx = runs.findIndex((r: unknown) => (r as { id: string }).id === run.id);
    if (idx >= 0) {
      (runs[idx] as Record<string, unknown>).status = result.success ? 'triggered' : 'failed';
      (runs[idx] as Record<string, unknown>).error = result.success ? undefined : result.error;
      (runs[idx] as Record<string, unknown>).run_data = result.data;
      fs.writeFileSync(getRunsLogPath(projectDir), JSON.stringify(runs, null, 2), 'utf-8');
    }

    return result;
  });

  ipcMain.handle('cicdTriggers:getRunStatus', async (_event, projectDir: string, runId: string) => {
    return runRunner(projectDir, ['--action', 'status', '--run-id', runId, '--project', projectDir, '--output-json']);
  });

  ipcMain.handle('cicdTriggers:cancelRun', async (_event, projectDir: string, runId: string) => {
    return runRunner(projectDir, ['--action', 'cancel', '--run-id', runId, '--project', projectDir, '--output-json']);
  });
}

export function setupCICDTriggersEventForwarding(_getMainWindow: () => BrowserWindow | null): void {
  // CI/CD triggers are request-response; pipeline events are polled via listRuns.
  // Future: webhook listener could push 'cicdTriggers:runUpdate' events.
}
