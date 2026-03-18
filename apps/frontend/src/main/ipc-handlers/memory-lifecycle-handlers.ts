/**
 * Memory Lifecycle Manager IPC Handlers (Feature 43)
 *
 * Exposes channels for managing Graphiti memory lifecycle:
 *   memoryLifecycle:getStatus    — Current memory stats + retention policy
 *   memoryLifecycle:listMemories — Paginated list of stored episodes
 *   memoryLifecycle:prune        — Run pruning with given policy
 *   memoryLifecycle:setPolicy    — Update retention policy
 *   memoryLifecycle:deleteMemory — Delete a specific episode by ID
 *   memoryLifecycle:export       — Export memories to JSON
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
    __dirname, '..', '..', '..', '..', '..', 'apps', 'backend', 'runners', 'memory_lifecycle_runner.py',
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

/** Read retention policy from project .env */
function readPolicy(projectDir: string): Record<string, string> {
  const envPath = path.join(projectDir, '.env');
  const result: Record<string, string> = {};
  if (!fs.existsSync(envPath)) return result;
  try {
    for (const line of fs.readFileSync(envPath, 'utf-8').split('\n')) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('MEMORY_')) continue;
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx < 0) continue;
      result[trimmed.slice(0, eqIdx).trim()] = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
    }
  } catch { /* ignore */ }
  return result;
}

function writePolicy(projectDir: string, config: Record<string, string>): void {
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

export function registerMemoryLifecycleHandlers(): void {
  ipcMain.handle('memoryLifecycle:getStatus', (_event, projectDir: string) => {
    try {
      const policy = readPolicy(projectDir);
      const storageDir = path.join(projectDir, '.auto-claude', 'memory');
      let episodeCount = 0;
      let diskUsageBytes = 0;
      if (fs.existsSync(storageDir)) {
        for (const f of fs.readdirSync(storageDir)) {
          if (f.endsWith('.json')) {
            episodeCount++;
            try { diskUsageBytes += fs.statSync(path.join(storageDir, f)).size; } catch { /* ignore */ }
          }
        }
      }
      return {
        success: true,
        data: {
          episode_count: episodeCount,
          disk_usage_bytes: diskUsageBytes,
          graphiti_enabled: process.env['GRAPHITI_ENABLED'] === 'true' || policy['GRAPHITI_ENABLED'] === 'true',
          retention_days: Number(policy['MEMORY_RETENTION_DAYS'] ?? 90),
          max_episodes: Number(policy['MEMORY_MAX_EPISODES'] ?? 10000),
          prune_strategy: policy['MEMORY_PRUNE_STRATEGY'] ?? 'lru',
          auto_prune: policy['MEMORY_AUTO_PRUNE'] === 'true',
        },
      };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle('memoryLifecycle:listMemories', (_event, projectDir: string, page: number = 0, pageSize: number = 50) => {
    try {
      const storageDir = path.join(projectDir, '.auto-claude', 'memory');
      if (!fs.existsSync(storageDir)) return { success: true, data: { items: [], total: 0 } };
      const files = fs.readdirSync(storageDir).filter(f => f.endsWith('.json'));
      const total = files.length;
      const slice = files.slice(page * pageSize, (page + 1) * pageSize);
      const items = slice.map(f => {
        try {
          const raw = JSON.parse(fs.readFileSync(path.join(storageDir, f), 'utf-8'));
          return { id: f.replace('.json', ''), ...raw };
        } catch {
          return { id: f.replace('.json', ''), error: 'parse_error' };
        }
      });
      return { success: true, data: { items, total, page, page_size: pageSize } };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle('memoryLifecycle:prune', async (_event, projectDir: string, options: {
    strategy?: string;
    max_age_days?: number;
    max_count?: number;
    dry_run?: boolean;
  } = {}) => {
    return runRunner(projectDir, [
      '--action', 'prune',
      '--project', projectDir,
      ...(options.strategy ? ['--strategy', options.strategy] : []),
      ...(options.max_age_days != null ? ['--max-age-days', String(options.max_age_days)] : []),
      ...(options.max_count != null ? ['--max-count', String(options.max_count)] : []),
      ...(options.dry_run ? ['--dry-run'] : []),
      '--output-json',
    ]);
  });

  ipcMain.handle('memoryLifecycle:setPolicy', (_event, projectDir: string, policy: {
    retention_days?: number;
    max_episodes?: number;
    prune_strategy?: string;
    auto_prune?: boolean;
  }) => {
    try {
      const envConfig: Record<string, string> = {};
      if (policy.retention_days != null) envConfig['MEMORY_RETENTION_DAYS'] = String(policy.retention_days);
      if (policy.max_episodes != null) envConfig['MEMORY_MAX_EPISODES'] = String(policy.max_episodes);
      if (policy.prune_strategy != null) envConfig['MEMORY_PRUNE_STRATEGY'] = policy.prune_strategy;
      if (policy.auto_prune != null) envConfig['MEMORY_AUTO_PRUNE'] = policy.auto_prune ? 'true' : 'false';
      writePolicy(projectDir, envConfig);
      return { success: true };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle('memoryLifecycle:deleteMemory', (_event, projectDir: string, episodeId: string) => {
    try {
      const filePath = path.join(projectDir, '.auto-claude', 'memory', `${episodeId}.json`);
      if (fs.existsSync(filePath)) { fs.unlinkSync(filePath); }
      return { success: true };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle('memoryLifecycle:export', (_event, projectDir: string, outputPath: string) => {
    try {
      const storageDir = path.join(projectDir, '.auto-claude', 'memory');
      const memories: unknown[] = [];
      if (fs.existsSync(storageDir)) {
        for (const f of fs.readdirSync(storageDir).filter(n => n.endsWith('.json'))) {
          try { memories.push(JSON.parse(fs.readFileSync(path.join(storageDir, f), 'utf-8'))); }
          catch { /* skip */ }
        }
      }
      fs.mkdirSync(path.dirname(outputPath), { recursive: true });
      fs.writeFileSync(outputPath, JSON.stringify(memories, null, 2), 'utf-8');
      return { success: true, data: { count: memories.length, path: outputPath } };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });
}

export function setupMemoryLifecycleEventForwarding(_getMainWindow: () => BrowserWindow | null): void {
  // Memory lifecycle is request-response; no persistent event stream needed.
  // Future: could emit 'memoryLifecycle:pruneProgress' events for long prune runs.
}
