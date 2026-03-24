/**
 * Team Knowledge Sync IPC Handlers (Feature 31)
 *
 * Exposes request-response channels for managing shared team memory:
 *   teamSync:getStatus        — Current sync config + peer list
 *   teamSync:push             — Export local snapshot to shared location
 *   teamSync:pull             — Import peer snapshots
 *   teamSync:listPeers        — List team members with published snapshots
 *   teamSync:getPeerEpisodes  — Fetch episodes imported from a specific peer
 *   teamSync:configure        — Update sync config in project .env
 *   teamSync:startServer      — Start HTTP server in background
 *   teamSync:stopServer       — Stop running HTTP server
 */

import { ipcMain } from 'electron';
import { spawn, type ChildProcess } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { getConfiguredPythonPath } from '../python-env-manager';
import { parsePythonCommand } from '../python-detector';

/** Currently running HTTP server process (one per app session). */
let _serverProcess: ChildProcess | null = null;
let _serverPort = 7749;

function getRunnerPath(): string {
  // Works both in dev and packaged builds (runner is in apps/backend)
  return path.join(__dirname, '..', '..', '..', '..', '..', 'apps', 'backend', 'runners', 'team_sync_runner.py');
}

function buildEnv(projectDir: string, config: Record<string, string> = {}): Record<string, string> {
  const envFilePath = path.join(projectDir, '.env');
  const baseEnv: Record<string, string> = { ...process.env } as Record<string, string>;
  if (fs.existsSync(envFilePath)) {
    try {
      const lines = fs.readFileSync(envFilePath, 'utf-8').split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        const eqIdx = trimmed.indexOf('=');
        if (eqIdx < 0) continue;
        const key = trimmed.slice(0, eqIdx).trim();
        const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
        baseEnv[key] = val;
      }
    } catch {
      // ignore
    }
  }
  return { ...baseEnv, ...config };
}

async function runPythonRunner(
  projectDir: string,
  args: string[],
  extraEnv: Record<string, string> = {},
): Promise<{ success: boolean; data?: unknown; error?: string }> {
  const pythonPath = await getConfiguredPythonPath(projectDir);
  const [cmd, baseArgs] = parsePythonCommand(pythonPath);
  const cmdArgs = [...baseArgs, getRunnerPath(), ...args];

  return new Promise((resolve) => {
    const env = buildEnv(projectDir, extraEnv);
    const proc = spawn(cmd, cmdArgs, { env, cwd: projectDir });

    const stdout: string[] = [];
    const stderr: string[] = [];
    proc.stdout?.on('data', (d: Buffer) => stdout.push(d.toString()));
    proc.stderr?.on('data', (d: Buffer) => stderr.push(d.toString()));

    proc.on('close', (code) => {
      const output = stdout.join('').trim();
      if (code === 0) {
        try {
          resolve({ success: true, data: JSON.parse(output) });
        } catch {
          resolve({ success: true, data: { message: output } });
        }
      } else {
        resolve({ success: false, error: stderr.join('').trim() || output });
      }
    });

    proc.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });
  });
}

/** Read current team sync configuration from project .env */
function readSyncConfig(projectDir: string): Record<string, string> {
  const envPath = path.join(projectDir, '.env');
  const result: Record<string, string> = {};
  if (!fs.existsSync(envPath)) return result;
  try {
    const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('TEAM_SYNC_')) continue;
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx < 0) continue;
      const key = trimmed.slice(0, eqIdx).trim();
      const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
      result[key] = val;
    }
  } catch {
    // ignore
  }
  return result;
}

/** Write team sync configuration keys into the project .env file. */
function writeSyncConfig(projectDir: string, config: Record<string, string>): void {
  const envPath = path.join(projectDir, '.env');
  let content = '';
  try {
    content = fs.existsSync(envPath) ? fs.readFileSync(envPath, 'utf-8') : '';
  } catch {
    content = '';
  }

  for (const [key, value] of Object.entries(config)) {
    const regex = new RegExp(`^${key}=.*$`, 'm');
    const line = `${key}=${value}`;
    if (regex.test(content)) {
      content = content.replace(regex, line);
    } else {
      content = content.trimEnd() + '\n' + line + '\n';
    }
  }

  fs.mkdirSync(projectDir, { recursive: true });
  fs.writeFileSync(envPath, content, 'utf-8');
}

/** Build a status object from local .auto-claude data without spawning Python. */
function getLocalStatus(projectDir: string): object {
  const config = readSyncConfig(projectDir);
  const syncPath = config['TEAM_SYNC_PATH'] || '';
  const teamId = config['TEAM_SYNC_TEAM_ID'] || 'default';
  const memberId = config['TEAM_SYNC_MEMBER_ID'] || '';
  const mode = config['TEAM_SYNC_MODE'] || 'directory';
  const serverUrl = config['TEAM_SYNC_SERVER_URL'] || '';
  const enabled = mode === 'directory' ? Boolean(syncPath) : Boolean(serverUrl);

  let peers: string[] = [];
  let localEpisodeCount = 0;
  let importedEpisodeCount = 0;
  let lastExport: string | null = null;

  if (enabled && mode === 'directory' && syncPath) {
    const teamDir = path.join(syncPath, teamId);
    try {
      if (fs.existsSync(teamDir)) {
        peers = fs
          .readdirSync(teamDir)
          .filter((f) => f.endsWith('_snapshot.json') && f !== `${memberId}_snapshot.json`)
          .map((f) => f.replace('_snapshot.json', ''));

        const ownSnapshot = path.join(teamDir, `${memberId}_snapshot.json`);
        if (fs.existsSync(ownSnapshot)) {
          const snap = JSON.parse(fs.readFileSync(ownSnapshot, 'utf-8'));
          localEpisodeCount = snap.episode_count ?? 0;
          lastExport = snap.exported_at ?? null;
        }
      }
    } catch {
      // ignore
    }
  }

  const peersDir = path.join(projectDir, '.auto-claude', 'team_sync', 'peers');
  try {
    if (fs.existsSync(peersDir)) {
      for (const peer of fs.readdirSync(peersDir)) {
        const epFile = path.join(peersDir, peer, 'imported_episodes.json');
        if (fs.existsSync(epFile)) {
          const data = JSON.parse(fs.readFileSync(epFile, 'utf-8'));
          importedEpisodeCount += Array.isArray(data) ? data.length : 0;
        }
      }
    }
  } catch {
    // ignore
  }

  return {
    enabled,
    mode,
    team_id: teamId,
    member_id: memberId,
    sync_path: syncPath,
    server_url: serverUrl,
    peers,
    last_export: lastExport,
    local_episode_count: localEpisodeCount,
    imported_episode_count: importedEpisodeCount,
    server_running: _serverProcess !== null,
    server_port: _serverPort,
  };
}

export function registerTeamSyncHandlers(): void {
  // ── Get status ─────────────────────────────────────────────────────────────
  ipcMain.handle(
    IPC_CHANNELS.TEAM_SYNC_GET_STATUS,
    (_event, projectDir: string): { success: boolean; data?: object; error?: string } => {
      try {
        return { success: true, data: getLocalStatus(projectDir) };
      } catch (err) {
        return { success: false, error: String(err) };
      }
    },
  );

  // ── Push ───────────────────────────────────────────────────────────────────
  ipcMain.handle(
    IPC_CHANNELS.TEAM_SYNC_PUSH,
    async (_event, projectDir: string): Promise<{ success: boolean; data?: unknown; error?: string }> => {
      try {
        return await runPythonRunner(projectDir, ['--push', '--project', projectDir, '--output-json']);
      } catch (err) {
        return { success: false, error: String(err) };
      }
    },
  );

  // ── Pull ───────────────────────────────────────────────────────────────────
  ipcMain.handle(
    IPC_CHANNELS.TEAM_SYNC_PULL,
    async (_event, projectDir: string): Promise<{ success: boolean; data?: unknown; error?: string }> => {
      try {
        return await runPythonRunner(projectDir, ['--pull', '--project', projectDir, '--output-json']);
      } catch (err) {
        return { success: false, error: String(err) };
      }
    },
  );

  // ── List peers ─────────────────────────────────────────────────────────────
  ipcMain.handle(
    IPC_CHANNELS.TEAM_SYNC_LIST_PEERS,
    (_event, projectDir: string): { success: boolean; data?: object[]; error?: string } => {
      try {
        const config = readSyncConfig(projectDir);
        const syncPath = config['TEAM_SYNC_PATH'] || '';
        const teamId = config['TEAM_SYNC_TEAM_ID'] || 'default';
        const memberId = config['TEAM_SYNC_MEMBER_ID'] || '';
        if (!syncPath) return { success: true, data: [] };

        const teamDir = path.join(syncPath, teamId);
        if (!fs.existsSync(teamDir)) return { success: true, data: [] };

        const peers: object[] = [];
        for (const f of fs.readdirSync(teamDir)) {
          if (!f.endsWith('_snapshot.json')) continue;
          try {
            const snap = JSON.parse(fs.readFileSync(path.join(teamDir, f), 'utf-8'));
            peers.push({
              member_id: snap.member_id || f.replace('_snapshot.json', ''),
              exported_at: snap.exported_at ?? null,
              episode_count: snap.episode_count ?? 0,
              project: snap.project ?? '',
              is_self: snap.member_id === memberId,
            });
          } catch {
            peers.push({ member_id: f.replace('_snapshot.json', ''), exported_at: null, episode_count: 0, project: '', is_self: false });
          }
        }
        return { success: true, data: peers };
      } catch (err) {
        return { success: false, error: String(err) };
      }
    },
  );

  // ── Get peer episodes ──────────────────────────────────────────────────────
  ipcMain.handle(
    IPC_CHANNELS.TEAM_SYNC_GET_PEER_EPISODES,
    (_event, projectDir: string, memberId: string): { success: boolean; data?: object[]; error?: string } => {
      try {
        const epFile = path.join(projectDir, '.auto-claude', 'team_sync', 'peers', memberId, 'imported_episodes.json');
        if (!fs.existsSync(epFile)) return { success: true, data: [] };
        const data = JSON.parse(fs.readFileSync(epFile, 'utf-8'));
        return { success: true, data: Array.isArray(data) ? data : [] };
      } catch (err) {
        return { success: false, error: String(err) };
      }
    },
  );

  // ── Configure ──────────────────────────────────────────────────────────────
  ipcMain.handle(
    IPC_CHANNELS.TEAM_SYNC_CONFIGURE,
    (
      _event,
      projectDir: string,
      config: {
        mode?: string;
        sync_path?: string;
        team_id?: string;
        member_id?: string;
        server_url?: string;
        server_host?: string;
        server_port?: number;
        auto_sync_interval?: number;
        auto_push?: boolean;
      },
    ): { success: boolean; error?: string } => {
      try {
        const envConfig: Record<string, string> = {};
        if (config.mode !== undefined) envConfig['TEAM_SYNC_MODE'] = config.mode;
        if (config.sync_path !== undefined) envConfig['TEAM_SYNC_PATH'] = config.sync_path;
        if (config.team_id !== undefined) envConfig['TEAM_SYNC_TEAM_ID'] = config.team_id;
        if (config.member_id !== undefined) envConfig['TEAM_SYNC_MEMBER_ID'] = config.member_id;
        if (config.server_url !== undefined) envConfig['TEAM_SYNC_SERVER_URL'] = config.server_url;
        if (config.server_host !== undefined) envConfig['TEAM_SYNC_SERVER_HOST'] = config.server_host;
        if (config.server_port !== undefined) envConfig['TEAM_SYNC_SERVER_PORT'] = String(config.server_port);
        if (config.auto_sync_interval !== undefined) envConfig['TEAM_SYNC_AUTO_SYNC_INTERVAL'] = String(config.auto_sync_interval);
        if (config.auto_push !== undefined) envConfig['TEAM_SYNC_AUTO_PUSH'] = config.auto_push ? 'true' : 'false';

        writeSyncConfig(projectDir, envConfig);
        return { success: true };
      } catch (err) {
        return { success: false, error: String(err) };
      }
    },
  );

  // ── Start HTTP server ──────────────────────────────────────────────────────
  ipcMain.handle(
    IPC_CHANNELS.TEAM_SYNC_START_SERVER,
    async (
      event,
      projectDir: string,
      port?: number,
    ): Promise<{ success: boolean; port?: number; error?: string }> => {
      if (_serverProcess) {
        return { success: true, port: _serverPort };
      }
      try {
        const pythonPath = await getConfiguredPythonPath(projectDir);
        const [cmd, baseArgs] = parsePythonCommand(pythonPath);
        const cmdArgs = [
          ...baseArgs,
          getRunnerPath(),
          '--serve',
          '--project', projectDir,
          ...(port ? ['--port', String(port)] : []),
        ];
        _serverPort = port ?? 7749;
        _serverProcess = spawn(cmd, cmdArgs, {
          env: buildEnv(projectDir),
          cwd: projectDir,
          detached: false,
        });
        _serverProcess.on('exit', () => { _serverProcess = null; });
        _serverProcess.stderr?.on('data', (d: Buffer) => console.warn('[TeamSync Server]', d.toString().trim()));
        // Give it a moment to start
        await new Promise((r) => setTimeout(r, 800));
        const sender = event.sender;
        sender.send(IPC_CHANNELS.TEAM_SYNC_SERVER_STATUS, { running: true, port: _serverPort });
        return { success: true, port: _serverPort };
      } catch (err) {
        _serverProcess = null;
        return { success: false, error: String(err) };
      }
    },
  );

  // ── Stop HTTP server ───────────────────────────────────────────────────────
  ipcMain.handle(
    IPC_CHANNELS.TEAM_SYNC_STOP_SERVER,
    (event): { success: boolean } => {
      if (_serverProcess) {
        _serverProcess.kill('SIGTERM');
        _serverProcess = null;
      }
      event.sender.send(IPC_CHANNELS.TEAM_SYNC_SERVER_STATUS, { running: false, port: _serverPort });
      return { success: true };
    },
  );
}
