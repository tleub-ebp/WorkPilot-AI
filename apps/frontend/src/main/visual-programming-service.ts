import { spawn, ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { EventEmitter } from 'node:events';
import { app } from 'electron';
import { getEffectiveSourcePath } from './updater/path-resolver';

export interface GeneratedFile {
  filename: string;
  language: string;
  content: string;
}

export interface GenerateCodeResult {
  files: GeneratedFile[];
  summary: string;
  instructions: string;
}

export interface DiagramNode {
  id: string;
  label: string;
  type: string;
  framework: string;
}

export interface DiagramEdge {
  source: string;
  target: string;
  label: string;
}

export interface CodeToVisualResult {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  summary: string;
}

export interface VisualProgrammingRequest {
  action: 'generate-code' | 'code-to-visual';
  // generate-code
  diagramJson?: string;
  framework?: string;
  // code-to-visual
  filePath?: string;
  projectPath?: string;
}

/**
 * Service for visual programming AI features.
 *
 * Events:
 * - 'status'  (msg: string)                           — progress update
 * - 'error'   (err: string)                           — error message
 * - 'complete' (result: GenerateCodeResult | CodeToVisualResult) — done
 */
export class VisualProgrammingService extends EventEmitter {
  private activeProcess: ChildProcess | null = null;
  private pythonPath = 'python';
  private sourcePath: string | null = null;

  configure(pythonPath?: string, sourcePath?: string): void {
    if (pythonPath) this.pythonPath = pythonPath;
    if (sourcePath) this.sourcePath = sourcePath;
  }

  private getSourcePath(): string | null {
    if (this.sourcePath) return this.sourcePath;
    const resolved = getEffectiveSourcePath();
    if (existsSync(path.join(resolved, 'runners', 'visual_programming_runner.py'))) {
      this.sourcePath = resolved;
      return resolved;
    }
    return null;
  }

  cancel(): boolean {
    if (!this.activeProcess) return false;
    this.activeProcess.kill();
    this.activeProcess = null;
    return true;
  }

  async run(request: VisualProgrammingRequest): Promise<void> {
    this.cancel();

    const sourcePath = this.getSourcePath();
    if (!sourcePath) {
      this.emit('error', 'WorkPilot AI source not found. Cannot locate visual_programming_runner.py');
      return;
    }

    const runnerPath = path.join(sourcePath, 'runners', 'visual_programming_runner.py');
    if (!existsSync(runnerPath)) {
      this.emit('error', 'visual_programming_runner.py not found');
      return;
    }

    const args = [runnerPath, '--action', request.action];

    if (request.action === 'generate-code') {
      if (!request.diagramJson) {
        this.emit('error', 'diagramJson is required for generate-code');
        return;
      }
      args.push('--diagram-json', request.diagramJson);
      if (request.framework) args.push('--framework', request.framework);
    } else {
      if (!request.filePath) {
        this.emit('error', 'filePath is required for code-to-visual');
        return;
      }
      args.push('--file-path', request.filePath);
      if (request.projectPath) args.push('--project-path', request.projectPath);
    }

    this.emit('status', `Starting ${request.action}…`);

    const env = this.buildEnv();
    await this.executeProcess(args, env, sourcePath);
  }

  private buildEnv(): Record<string, string> {
    const env: Record<string, string> = { ...(process.env as Record<string, string>) };
    try {
      const settingsPath = path.join(app.getPath('userData'), 'settings.json');
      if (existsSync(settingsPath)) {
        const { readFileSync } = require('node:fs');
        const settings = JSON.parse(readFileSync(settingsPath, 'utf-8'));
        if (settings.globalClaudeOAuthToken) env.CLAUDE_OAUTH_TOKEN = settings.globalClaudeOAuthToken;
        if (settings.globalAnthropicApiKey) env.ANTHROPIC_API_KEY = settings.globalAnthropicApiKey;
      }
    } catch { /* ignore */ }
    return env;
  }

  private async executeProcess(args: string[], env: Record<string, string>, cwd: string): Promise<void> {
    const proc = spawn(this.pythonPath, args, { cwd, env, stdio: ['pipe', 'pipe', 'pipe'] });
    this.activeProcess = proc;

    let stderrOutput = '';

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      for (const line of text.split('\n')) {
        if (line.startsWith('__VIS_PROG_RESULT__:')) {
          try {
            const payload = JSON.parse(line.substring('__VIS_PROG_RESULT__:'.length));
            this.emit('complete', payload);
          } catch { /* ignore parse errors */ }
        } else if (line.startsWith('__VIS_PROG_ERROR__:')) {
          this.emit('error', line.substring('__VIS_PROG_ERROR__:'.length));
        } else if (line.trim()) {
          this.emit('status', line.trim());
        }
      }
    });

    proc.stderr?.on('data', (data: Buffer) => {
      stderrOutput = (stderrOutput + data.toString('utf-8')).slice(-5000);
      console.error('[VisualProg]', data.toString('utf-8'));
    });

    proc.on('close', (code) => {
      this.activeProcess = null;
      if (code !== 0 && code !== null) {
        this.emit('error', `Process exited with code ${code}. ${stderrOutput.slice(-500)}`);
      }
    });

    proc.on('error', (err) => {
      this.activeProcess = null;
      this.emit('error', `Failed to start process: ${err.message}`);
    });
  }
}

export const visualProgrammingService = new VisualProgrammingService();
