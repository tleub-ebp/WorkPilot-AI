import { spawn, ChildProcess } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';
import { app } from 'electron';
import { MODEL_ID_MAP } from '../shared/constants';
import type { AppSettings } from '../shared/types';

/**
 * Result of natural language Git command execution
 */
export interface NaturalLanguageGitResult {
  generatedCommand: string;
  explanation: string;
  executionOutput: string;
  success: boolean;
}

/**
 * Configuration for a natural language Git request
 */
export interface NaturalLanguageGitRequest {
  projectPath: string;
  command: string;
  model?: string;
  thinkingLevel?: string;
}

/**
 * Service for natural language Git command processing
 *
 * Spawns the Python natural_language_git_runner.py process and streams output
 * back to the renderer via events.
 *
 * Events emitted:
 * - 'status' (status: string) — Status update message
 * - 'stream-chunk' (chunk: string) — Streaming text output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: NaturalLanguageGitResult) — Command execution complete with structured result
 */
export class NaturalLanguageGitService extends EventEmitter {
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
      const runnerPath = path.join(p, 'runners', 'natural_language_git_runner.py');
      if (existsSync(runnerPath)) {
        this.autoBuildSourcePath = p;
        return p;
      }
    }

    return null;
  }

  /**
   * Cancel any active command execution
   */
  cancel(): boolean {
    if (!this.activeProcess) return false;
    this.activeProcess.kill();
    this.activeProcess = null;
    return true;
  }

  /**
   * Execute natural language Git command
   */
  async execute(request: NaturalLanguageGitRequest): Promise<void> {
    // Cancel any existing process
    this.cancel();

    const autoBuildSource = this.getAutoBuildSourcePath();
    if (!autoBuildSource) {
      this.emit('error', 'WorkPilot AI source not found. Cannot locate natural_language_git_runner.py');
      return;
    }

    const runnerPath = path.join(autoBuildSource, 'runners', 'natural_language_git_runner.py');
    if (!existsSync(runnerPath)) {
      this.emit('error', 'natural_language_git_runner.py not found in auto-claude directory');
      return;
    }

    // Emit initial status
    this.emit('status', 'Processing natural language command...');

    // Build command arguments
    const args = [
      runnerPath,
      '--project-dir', request.projectPath,
      '--command', request.command,
    ];

    // Add model config if provided
    if (request.model) {
      const modelId = MODEL_ID_MAP[request.model] || request.model;
      args.push('--model', modelId);
    }
    if (request.thinkingLevel) {
      args.push('--thinking-level', request.thinkingLevel);
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
    let gitResult: NaturalLanguageGitResult | null = null;

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      const lines = text.split('\n');

      for (const line of lines) {
        // Check for the structured result marker
        if (line.startsWith('__GIT_RESULT__:')) {
          try {
            const jsonStr = line.substring('__GIT_RESULT__:'.length);
            gitResult = JSON.parse(jsonStr);
            this.emit('status', 'Command executed');
          } catch (parseErr) {
            console.error('[NaturalLanguageGit] Failed to parse result:', parseErr);
          }
        } else if (line.startsWith('__STATUS__:')) {
          // Handle status updates
          const status = line.substring('__STATUS__:'.length);
          this.emit('status', status);
        } else if (line.startsWith('__ERROR__:')) {
          // Handle error messages
          const error = line.substring('__ERROR__:'.length);
          this.emit('error', error);
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
      console.error('[NaturalLanguageGit]', text);
    });

    proc.on('close', (code) => {
      this.activeProcess = null;

      if (code === 0 && gitResult) {
        this.emit('complete', gitResult);
      } else if (code !== 0) {
        // Check for common error patterns
        const combinedOutput = fullOutput + stderrOutput;
        if (combinedOutput.includes('rate_limit') || combinedOutput.includes('Rate limit')) {
          this.emit('error', 'Rate limit reached. Please try again in a few moments.');
        } else if (combinedOutput.includes('authentication') || combinedOutput.includes('CLAUDE_OAUTH_TOKEN')) {
          this.emit('error', 'Authentication error. Please check your Claude credentials in Settings.');
        } else {
          this.emit('error', `Command execution failed (exit code ${code}). ${stderrOutput.slice(-500)}`);
        }
      } else {
        // Process completed but no structured result found
        if (fullOutput.trim()) {
          this.emit('error', `Command completed but no structured result: ${fullOutput.trim()}`);
        } else {
          this.emit('error', 'Command execution completed but produced no output.');
        }
      }
    });

    proc.on('error', (err) => {
      this.activeProcess = null;
      this.emit('error', `Failed to start Git processor: ${err.message}`);
    });
  }
}

// Singleton instance
export const naturalLanguageGitService = new NaturalLanguageGitService();
