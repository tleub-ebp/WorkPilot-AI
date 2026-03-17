import { spawn, ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { EventEmitter } from 'node:events';
import { app } from 'electron';
import { MODEL_ID_MAP } from '../shared/constants';
import type { AppSettings } from '../shared/types';

export interface ArchitectureVisualizerResult {
  status: string;
  diagrams: Record<string, {
    diagram_type: string;
    title: string;
    nodes: Array<{ id: string; name: string; path: string; type: string; language: string }>;
    edges: Array<{ source_id: string; target_id: string; edge_type: string; label: string }>;
    mermaid_code: string;
    generated_at: string;
  }>;
  project_dir: string;
  diagram_types_analyzed: string[];
  output_dir: string;
  summary: {
    total_diagrams: number;
    total_nodes: number;
    total_edges: number;
    diagram_types: string[];
  };
}

export interface ArchitectureVisualizerRequest {
  projectDir: string;
  diagramTypes?: string[];
  outputDir?: string;
  model?: string;
  thinkingLevel?: string;
}

/**
 * Service for AI-powered architecture diagram generation.
 *
 * Events:
 * - 'status' (status: string) — Status update
 * - 'stream-chunk' (chunk: string) — Streaming text output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: ArchitectureVisualizerResult) — Generation complete
 */
export class ArchitectureVisualizerService extends EventEmitter {
  private activeProcess: ChildProcess | null = null;
  private pythonPath = 'python';
  private autoBuildSourcePath: string | null = null;

  configure(pythonPath?: string, autoBuildSourcePath?: string): void {
    if (pythonPath) this.pythonPath = pythonPath;
    if (autoBuildSourcePath) this.autoBuildSourcePath = autoBuildSourcePath;
  }

  private getAutoBuildSourcePath(): string | null {
    if (this.autoBuildSourcePath) return this.autoBuildSourcePath;
    const possiblePaths = [
      path.join(app.getPath('userData'), '..', 'auto-claude'),
      path.join(process.cwd(), 'apps', 'backend'),
    ];
    for (const p of possiblePaths) {
      if (existsSync(path.join(p, 'runners', 'architecture_visualizer_runner.py'))) {
        this.autoBuildSourcePath = p;
        return p;
      }
    }
    return null;
  }

  cancel(): boolean {
    if (!this.activeProcess) return false;
    this.activeProcess.kill();
    this.activeProcess = null;
    return true;
  }

  async generate(request: ArchitectureVisualizerRequest): Promise<void> {
    this.cancel();
    const sourcePath = this.getAutoBuildSourcePath();
    if (!sourcePath) {
      this.emit('error', 'WorkPilot AI source not found. Cannot locate architecture_visualizer_runner.py');
      return;
    }
    const runnerPath = path.join(sourcePath, 'runners', 'architecture_visualizer_runner.py');
    if (!existsSync(runnerPath)) {
      this.emit('error', 'architecture_visualizer_runner.py not found');
      return;
    }

    this.emit('status', 'Initializing Architecture Visualizer...');

    const args = [runnerPath, '--project-dir', request.projectDir];
    if (request.diagramTypes?.length) {
      args.push('--diagram-types', request.diagramTypes.join(','));
    }
    if (request.outputDir) args.push('--output-dir', request.outputDir);
    if (request.model) {
      const modelId = MODEL_ID_MAP[request.model] || request.model;
      args.push('--model', modelId);
    }
    if (request.thinkingLevel) args.push('--thinking-level', request.thinkingLevel);

    const env = this.buildProcessEnvironment();
    await this.executeProcess(args, env, sourcePath);
  }

  private buildProcessEnvironment(): Record<string, string> {
    const env: Record<string, string> = { ...process.env as Record<string, string> };
    try {
      const settingsPath = path.join(app.getPath('userData'), 'settings.json');
      if (existsSync(settingsPath)) {
        const { readFileSync } = require('node:fs');
        const settings: AppSettings = JSON.parse(readFileSync(settingsPath, 'utf-8'));
        if (settings.globalClaudeOAuthToken) env.CLAUDE_OAUTH_TOKEN = settings.globalClaudeOAuthToken;
        if (settings.globalAnthropicApiKey) env.ANTHROPIC_API_KEY = settings.globalAnthropicApiKey;
      }
    } catch { /* ignore */ }
    return env;
  }

  private async executeProcess(args: string[], env: Record<string, string>, cwd: string): Promise<void> {
    const proc = spawn(this.pythonPath, args, { cwd, env, stdio: ['pipe', 'pipe', 'pipe'] });
    this.activeProcess = proc;

    let fullOutput = '';
    let stderrOutput = '';
    let result: ArchitectureVisualizerResult | null = null;

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      for (const line of text.split('\n')) {
        if (line.startsWith('__ARCH_VIZ_RESULT__:')) {
          try {
            result = JSON.parse(line.substring('__ARCH_VIZ_RESULT__:'.length));
            this.emit('status', 'Analysis complete');
          } catch { /* ignore */ }
        } else if (line.trim()) {
          fullOutput += line + '\n';
          this.emit('stream-chunk', line + '\n');
        }
      }
    });

    proc.stderr?.on('data', (data: Buffer) => {
      stderrOutput = (stderrOutput + data.toString('utf-8')).slice(-5000);
      console.error('[ArchViz]', data.toString('utf-8'));
    });

    proc.on('close', (code) => {
      this.activeProcess = null;
      if (code === 0 && result) {
        this.emit('complete', result);
      } else if (code === 0 && fullOutput.trim()) {
        this.emit('complete', { status: 'success', diagrams: {}, summary: { total_diagrams: 0, total_nodes: 0, total_edges: 0, diagram_types: [] }, raw_output: fullOutput });
      } else {
        this.emit('error', `Architecture visualization failed (exit code ${code}). ${stderrOutput.slice(-500)}`);
      }
    });

    proc.on('error', (err) => {
      this.activeProcess = null;
      this.emit('error', `Failed to start architecture visualizer: ${err.message}`);
    });
  }
}

export const architectureVisualizerService = new ArchitectureVisualizerService();
