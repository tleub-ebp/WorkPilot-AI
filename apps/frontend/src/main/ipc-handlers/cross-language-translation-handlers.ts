/**
 * Cross-Language Translation Agent IPC Handlers (Feature 41)
 *
 * Exposes channels for AI-powered code translation between programming languages:
 *   crossLangTranslation:getSupportedLanguages — List of supported source/target languages
 *   crossLangTranslation:translate             — Translate a file or snippet
 *   crossLangTranslation:cancel                — Cancel an in-progress translation
 *   crossLangTranslation:getHistory            — List recent translations
 *   crossLangTranslation:clearHistory          — Clear translation history
 *
 * Supported: Python↔TypeScript, TypeScript↔Python, Python↔Go, Java↔TypeScript, C#↔TypeScript
 */

import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { spawn, type ChildProcess } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { getConfiguredPythonPath } from '../python-env-manager';
import { parsePythonCommand } from '../python-detector';

function getRunnerPath(): string {
  return path.join(
    __dirname, '..', '..', '..', '..', '..', 'apps', 'backend', 'runners', 'cross_language_translation_runner.py',
  );
}

let _currentProcess: ChildProcess | null = null;

async function runRunner(
  projectDir: string,
  args: string[],
  onChunk?: (chunk: string) => void,
): Promise<{ success: boolean; data?: unknown; error?: string }> {
  if (_currentProcess) {
    _currentProcess.kill('SIGTERM');
    _currentProcess = null;
  }

  const pythonPath = getConfiguredPythonPath();
  const [cmd, pythonBaseArgs] = parsePythonCommand(pythonPath);
  const cmdArgs = [...pythonBaseArgs, getRunnerPath(), ...args];

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
          env[trimmed.slice(0, eqIdx).trim()] = trimmed.slice(eqIdx + 1).trim().replaceAll(/^["']|["']$/g, '');
        }
      } catch { /* ignore */ }
    }

    const proc = spawn(cmd, cmdArgs, { env, cwd: projectDir });
    _currentProcess = proc;
    const stdout: string[] = [];
    const stderr: string[] = [];
    proc.stdout?.on('data', (d: Buffer) => {
      const chunk = d.toString();
      stdout.push(chunk);
      onChunk?.(chunk);
    });
    proc.stderr?.on('data', (d: Buffer) => stderr.push(d.toString()));

    proc.on('close', (code) => {
      if (proc === _currentProcess) _currentProcess = null;
      const out = stdout.join('').trim();
      if (code === 0) {
        try { resolve({ success: true, data: JSON.parse(out) }); }
        catch { resolve({ success: true, data: { translated_code: out } }); }
      } else {
        resolve({ success: false, error: stderr.join('').trim() || out });
      }
    });
    proc.on('error', (err) => {
      if (proc === _currentProcess) _currentProcess = null;
      resolve({ success: false, error: err.message });
    });
  });
}

const SUPPORTED_LANGUAGES = [
  { id: 'python', label: 'Python', extension: '.py' },
  { id: 'typescript', label: 'TypeScript', extension: '.ts' },
  { id: 'javascript', label: 'JavaScript', extension: '.js' },
  { id: 'go', label: 'Go', extension: '.go' },
  { id: 'java', label: 'Java', extension: '.java' },
  { id: 'csharp', label: 'C#', extension: '.cs' },
  { id: 'rust', label: 'Rust', extension: '.rs' },
  { id: 'kotlin', label: 'Kotlin', extension: '.kt' },
  { id: 'swift', label: 'Swift', extension: '.swift' },
  { id: 'php', label: 'PHP', extension: '.php' },
];

function getHistoryPath(projectDir: string): string {
  return path.join(projectDir, '.auto-claude', 'translation_history.json');
}

function loadHistory(projectDir: string): object[] {
  const p = getHistoryPath(projectDir);
  if (!fs.existsSync(p)) return [];
  try { return JSON.parse(fs.readFileSync(p, 'utf-8')); }
  catch { return []; }
}

function appendHistory(projectDir: string, entry: object): void {
  const history = loadHistory(projectDir);
  history.unshift(entry);
  const trimmed = history.slice(0, 100);
  fs.mkdirSync(path.dirname(getHistoryPath(projectDir)), { recursive: true });
  fs.writeFileSync(getHistoryPath(projectDir), JSON.stringify(trimmed, null, 2), 'utf-8');
}

export function registerCrossLanguageTranslationHandlers(): void {
  ipcMain.handle('crossLangTranslation:getSupportedLanguages', () => ({
    success: true,
    data: SUPPORTED_LANGUAGES,
  }));

  ipcMain.handle('crossLangTranslation:translate', async (event, params: {
    projectDir: string;
    sourceLang: string;
    targetLang: string;
    code?: string;
    filePath?: string;
    outputPath?: string;
    preserveComments?: boolean;
    generateTests?: boolean;
  }) => {
    const historyEntry = {
      id: Date.now().toString(),
      started_at: new Date().toISOString(),
      source_lang: params.sourceLang,
      target_lang: params.targetLang,
      file_path: params.filePath ?? '',
      status: 'pending',
    };
    appendHistory(params.projectDir, historyEntry);

    const args = [
      '--action', 'translate',
      '--source-lang', params.sourceLang,
      '--target-lang', params.targetLang,
      '--project', params.projectDir,
      ...(params.filePath ? ['--file', params.filePath] : []),
      ...(params.outputPath ? ['--output', params.outputPath] : []),
      ...(params.preserveComments ? ['--preserve-comments'] : []),
      ...(params.generateTests ? ['--generate-tests'] : []),
      '--output-json',
    ];

    // If inline code, write to a temp file
    let tempFile: string | null = null;
    if (params.code && !params.filePath) {
      const ext = SUPPORTED_LANGUAGES.find(l => l.id === params.sourceLang)?.extension ?? '.txt';
      tempFile = path.join(params.projectDir, `.auto-claude`, `_translate_temp${ext}`);
      fs.mkdirSync(path.dirname(tempFile), { recursive: true });
      fs.writeFileSync(tempFile, params.code, 'utf-8');
      args.splice(args.indexOf('--file') + 1, 1, tempFile);
      if (!args.includes('--file')) args.push('--file', tempFile);
    }

    const result = await runRunner(params.projectDir, args, (chunk) => {
      event.sender.send('crossLangTranslation:streamChunk', chunk);
    });

    if (tempFile && fs.existsSync(tempFile)) {
      try { fs.unlinkSync(tempFile); } catch { /* ignore */ }
    }

    // Update history
    const history = loadHistory(params.projectDir);
    const idx = history.findIndex((h: unknown) => (h as { id: string }).id === historyEntry.id);
    if (idx >= 0) {
      (history[idx] as Record<string, unknown>).status = result.success ? 'complete' : 'failed';
      (history[idx] as Record<string, unknown>).completed_at = new Date().toISOString();
      fs.writeFileSync(getHistoryPath(params.projectDir), JSON.stringify(history, null, 2), 'utf-8');
    }

    event.sender.send('crossLangTranslation:complete', result);
    return result;
  });

  ipcMain.handle('crossLangTranslation:cancel', () => {
    if (_currentProcess) {
      _currentProcess.kill('SIGTERM');
      _currentProcess = null;
      return { success: true };
    }
    return { success: false, error: 'No translation in progress' };
  });

  ipcMain.handle('crossLangTranslation:getHistory', (_event, projectDir: string, limit: number = 50) => {
    try {
      const history = loadHistory(projectDir).slice(0, limit);
      return { success: true, data: history };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle('crossLangTranslation:clearHistory', (_event, projectDir: string) => {
    try {
      const p = getHistoryPath(projectDir);
      if (fs.existsSync(p)) { fs.unlinkSync(p); }
      return { success: true };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });
}

export function setupCrossLanguageTranslationEventForwarding(_getMainWindow: () => BrowserWindow | null): void {
  // Events are sent directly to the requesting window via event.sender.send() in the handlers.
  // No persistent main→renderer forwarding needed.
}
