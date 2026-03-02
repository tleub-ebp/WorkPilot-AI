import { spawn, ChildProcess } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';
import { app } from 'electron';
import { MODEL_ID_MAP } from '../shared/constants';
import type { AppSettings } from '../shared/types';

/**
 * Result of auto-refactor analysis
 */
export interface AutoRefactorResult {
  analysis: {
    status: string;
    analysis: any;
    files_analyzed: number;
  };
  plan: {
    status: string;
    plan: any;
  };
  execution: {
    status: string;
    execution: any;
    auto_executed: boolean;
  };
  summary: {
    issues_found: number;
    files_analyzed: number;
    refactoring_items: number;
    quick_wins: number;
    estimated_effort: string;
    risk_level: string;
  };
}

/**
 * Configuration for an auto-refactor request
 */
export interface AutoRefactorRequest {
  projectDir: string;
  model?: string;
  thinkingLevel?: string;
  autoExecute?: boolean;
}

/**
 * Service for AI-powered automatic refactoring
 *
 * Spawns the Python auto_refactor_runner.py process and streams output
 * back to the renderer via events.
 *
 * Events emitted:
 * - 'status' (status: string) — Status update message
 * - 'stream-chunk' (chunk: string) — Streaming text output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: AutoRefactorResult) — Analysis complete with structured result
 * - 'execution-complete' (result: any) — Execution complete (if auto-executed)
 */
export class AutoRefactorService extends EventEmitter {
  private activeProcess: ChildProcess | null = null;
  private pythonPath: string = 'python';
  private autoBuildSourcePath: string | null = null;

  constructor() {
    super();
  }

  /**
   * Configure paths for Python and auto-claude source
   */
  configure(pythonPath?: string, autoBuildSourcePath?: string): void {
    if (pythonPath) {
      this.pythonPath = pythonPath;
    }
    if (autoBuildSourcePath) {
      this.autoBuildSourcePath = autoBuildSourcePath;
    }
  }

  /**
   * Get the auto-build source path, resolving from settings if needed
   */
  private getAutoBuildSourcePath(): string | null {
    if (this.autoBuildSourcePath) return this.autoBuildSourcePath;

    // Try common locations
    const possiblePaths = [
      path.join(app.getPath('userData'), '..', 'auto-claude'),
      path.join(process.cwd(), 'apps', 'backend'),
    ];

    for (const p of possiblePaths) {
      const runnerPath = path.join(p, 'runners', 'auto_refactor_runner.py');
      if (existsSync(runnerPath)) {
        this.autoBuildSourcePath = p;
        return p;
      }
    }

    return null;
  }

  /**
   * Cancel any active analysis
   */
  cancel(): boolean {
    if (!this.activeProcess) return false;
    this.activeProcess.kill();
    this.activeProcess = null;
    return true;
  }

  /**
   * Run auto-refactor analysis
   */
  async analyze(request: AutoRefactorRequest): Promise<void> {
    // Cancel any existing process
    this.cancel();

    const autoBuildSource = this.getAutoBuildSourcePath();
    if (!autoBuildSource) {
      this.emit('error', 'WorkPilot AI source not found. Cannot locate auto_refactor_runner.py');
      return;
    }

    const runnerPath = path.join(autoBuildSource, 'runners', 'auto_refactor_runner.py');
    if (!existsSync(runnerPath)) {
      this.emit('error', 'auto_refactor_runner.py not found in auto-claude directory');
      return;
    }

    // Emit initial status
    this.emit('status', 'Initializing Auto-Refactor Agent...');

    // Build command arguments
    const args = [
      runnerPath,
      '--project-dir', request.projectDir,
    ];

    // Add model config if provided
    if (request.model) {
      const modelId = MODEL_ID_MAP[request.model] || request.model;
      args.push('--model', modelId);
    }
    if (request.thinkingLevel) {
      args.push('--thinking-level', request.thinkingLevel);
    }
    if (request.autoExecute) {
      args.push('--auto-execute');
    }

    // Build process environment
    const processEnv: Record<string, string> = {
      ...process.env as Record<string, string>,
    };

    // Read OAuth token from settings if available
    try {
      const settingsPath = path.join(app.getPath('userData'), 'settings.json');
      if (existsSync(settingsPath)) {
        const { readFileSync } = require('fs');
        const settings: AppSettings = JSON.parse(readFileSync(settingsPath, 'utf-8'));
        if (settings.globalClaudeOAuthToken) {
          processEnv.CLAUDE_OAUTH_TOKEN = settings.globalClaudeOAuthToken;
        }
        if (settings.globalAnthropicApiKey) {
          processEnv.ANTHROPIC_API_KEY = settings.globalAnthropicApiKey;
        }
      }
    } catch {
      // Ignore settings read errors
    }

    // Spawn Python process
    const proc = spawn(this.pythonPath, args, {
      cwd: autoBuildSource,
      env: processEnv,
    });

    this.activeProcess = proc;

    let fullOutput = '';
    let stderrOutput = '';
    let analysisResult: AutoRefactorResult | null = null;
    let executionResult: any = null;

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      const lines = text.split('\n');

      for (const line of lines) {
        // Check for the structured analysis result marker
        if (line.startsWith('__AUTO_REFACTOR_RESULT__:')) {
          try {
            const jsonStr = line.substring('__AUTO_REFACTOR_RESULT__:'.length);
            analysisResult = JSON.parse(jsonStr);
            this.emit('status', 'Analysis complete');
          } catch (parseErr) {
            console.error('[AutoRefactor] Failed to parse analysis result:', parseErr);
          }
        } else if (line.startsWith('__AUTO_REFACTOR_EXECUTION__:')) {
          try {
            const jsonStr = line.substring('__AUTO_REFACTOR_EXECUTION__:'.length);
            executionResult = JSON.parse(jsonStr);
            this.emit('status', 'Execution complete');
          } catch (parseErr) {
            console.error('[AutoRefactor] Failed to parse execution result:', parseErr);
          }
        } else if (line.startsWith('__TOOL_START__:')) {
          // Handle tool usage notifications
          try {
            const toolInfo = JSON.parse(line.substring('__TOOL_START__:'.length));
            this.emit('status', `Using ${toolInfo.tool}...`);
          } catch {
            // Ignore parse errors for tool notifications
          }
        } else if (line.startsWith('__TOOL_END__:')) {
          // Tool completed, continue
        } else if (line.trim()) {
          fullOutput += line + '\n';
          this.emit('stream-chunk', line + '\n');
        }
      }
    });

    proc.stderr?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      stderrOutput = (stderrOutput + text).slice(-5000);
      // Log but don't emit as error (stderr may contain progress info)
      console.error('[AutoRefactor]', text);
    });

    proc.on('close', (code) => {
      this.activeProcess = null;

      if (code === 0 && analysisResult) {
        this.emit('complete', analysisResult);
        if (executionResult) {
          this.emit('execution-complete', executionResult);
        }
      } else if (code !== 0) {
        // Check for common error patterns
        const combinedOutput = fullOutput + stderrOutput;
        if (combinedOutput.includes('rate_limit') || combinedOutput.includes('Rate limit')) {
          this.emit('error', 'Rate limit reached. Please try again in a few moments.');
        } else if (combinedOutput.includes('authentication') || combinedOutput.includes('CLAUDE_OAUTH_TOKEN')) {
          this.emit('error', 'Authentication error. Please check your Claude credentials in Settings.');
        } else {
          this.emit('error', `Analysis failed (exit code ${code}). ${stderrOutput.slice(-500)}`);
        }
      } else {
        // Process completed but no structured result found
        if (fullOutput.trim()) {
          // Try to create a basic result from raw output
          const fallbackResult: AutoRefactorResult = {
            analysis: {
              status: 'success',
              analysis: { raw_output: fullOutput.trim() },
              files_analyzed: 0,
            },
            plan: {
              status: 'success',
              plan: { raw_output: fullOutput.trim() },
            },
            execution: {
              status: 'success',
              execution: { raw_output: fullOutput.trim() },
              auto_executed: false,
            },
            summary: {
              issues_found: 0,
              files_analyzed: 0,
              refactoring_items: 0,
              quick_wins: 0,
              estimated_effort: 'Unknown',
              risk_level: 'Unknown',
            },
          };
          this.emit('complete', fallbackResult);
        } else {
          this.emit('error', 'Analysis completed but produced no output.');
        }
      }
    });

    proc.on('error', (err) => {
      this.activeProcess = null;
      this.emit('error', `Failed to start auto-refactor: ${err.message}`);
    });
  }
}

// Singleton instance
export const autoRefactorService = new AutoRefactorService();
