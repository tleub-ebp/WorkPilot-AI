import { spawn, ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { EventEmitter } from 'node:events';
import { app } from 'electron';
import { MODEL_ID_MAP } from '../shared/constants';
import type { AppSettings } from '../shared/types';

export interface PerformanceProfilerResult {
  status: string;
  report: {
    project_dir: string;
    bottlenecks: Array<{
      bottleneck_id: string;
      file_path: string;
      line_start: number;
      line_end: number;
      type: string;
      severity: string;
      description: string;
      estimated_impact: string;
      code_snippet: string;
    }>;
    suggestions: Array<{
      suggestion_id: string;
      bottleneck_id: string;
      title: string;
      description: string;
      implementation: string;
      estimated_improvement: string;
      effort: string;
      auto_implementable: boolean;
    }>;
    benchmarks: Array<{
      name: string;
      duration_ms: number;
      memory_mb: number;
      timestamp: string;
    }>;
    summary: {
      total_bottlenecks: number;
      critical_count: number;
      high_count: number;
      medium_count: number;
      low_count: number;
      total_suggestions: number;
      auto_implementable_suggestions: number;
    };
    generated_at: string;
  };
  summary: Record<string, unknown>;
}

export interface PerformanceProfilerRequest {
  projectDir: string;
  autoImplement?: boolean;
  model?: string;
  thinkingLevel?: string;
}

/**
 * Service for AI-powered performance profiling.
 *
 * Events:
 * - 'status' (status: string) — Status update
 * - 'stream-chunk' (chunk: string) — Streaming output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: PerformanceProfilerResult) — Profiling complete
 * - 'implementation-complete' (result: any) — Auto-impl complete
 */
export class PerformanceProfilerService extends EventEmitter {
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
      if (existsSync(path.join(p, 'runners', 'performance_profiler_runner.py'))) {
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

  async startProfiling(request: PerformanceProfilerRequest): Promise<void> {
    this.cancel();
    const sourcePath = this.getAutoBuildSourcePath();
    if (!sourcePath) {
      this.emit('error', 'WorkPilot AI source not found. Cannot locate performance_profiler_runner.py');
      return;
    }
    const runnerPath = path.join(sourcePath, 'runners', 'performance_profiler_runner.py');
    if (!existsSync(runnerPath)) {
      this.emit('error', 'performance_profiler_runner.py not found');
      return;
    }

    this.emit('status', 'Initializing Performance Profiler...');

    const args = [runnerPath, '--project-dir', request.projectDir];
    if (request.autoImplement) args.push('--auto-implement');
    if (request.model) args.push('--model', MODEL_ID_MAP[request.model] || request.model);
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
    let result: PerformanceProfilerResult | null = null;
    let implResult: unknown = null;

    proc.stdout?.on('data', (data: Buffer) => {
      for (const line of data.toString('utf-8').split('\n')) {
        if (line.startsWith('__PERF_RESULT__:')) {
          try { result = JSON.parse(line.substring('__PERF_RESULT__:'.length)); this.emit('status', 'Profiling complete'); } catch { /* ignore */ }
        } else if (line.startsWith('__PERF_IMPLEMENTATION__:')) {
          try { implResult = JSON.parse(line.substring('__PERF_IMPLEMENTATION__:'.length)); } catch { /* ignore */ }
        } else if (line.trim()) {
          fullOutput += line + '\n';
          this.emit('stream-chunk', line + '\n');
          if (line.includes('Phase')) this.emit('status', line.trim());
        }
      }
    });

    proc.stderr?.on('data', (data: Buffer) => {
      stderrOutput = (stderrOutput + data.toString('utf-8')).slice(-5000);
      console.error('[PerfProfiler]', data.toString('utf-8'));
    });

    proc.on('close', (code) => {
      this.activeProcess = null;
      if (code === 0 && result) {
        this.emit('complete', result);
        if (implResult) this.emit('implementation-complete', implResult);
      } else if (code === 0 && fullOutput.trim()) {
        this.emit('complete', { status: 'success', report: { bottlenecks: [], suggestions: [], benchmarks: [], summary: {}, generated_at: '' }, summary: {} });
      } else {
        this.emit('error', `Performance profiling failed (exit code ${code}). ${stderrOutput.slice(-500)}`);
      }
    });

    proc.on('error', (err) => {
      this.activeProcess = null;
      this.emit('error', `Failed to start performance profiler: ${err.message}`);
    });
  }
}

export const performanceProfilerService = new PerformanceProfilerService();
