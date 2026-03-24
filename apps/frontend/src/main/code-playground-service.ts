import { spawn, ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { EventEmitter } from 'node:events';
import { app } from 'electron';
import type { PlaygroundType, SandboxType } from '../renderer/stores/code-playground-store';
import { MODEL_ID_MAP } from '../shared/constants';
import type { AppSettings } from '../shared/types';

/**
 * Result of code playground generation
 */
export interface PlaygroundFile {
  path: string;
  content: string;
  size: number;
}

export interface PlaygroundResult {
  html?: string;
  css?: string;
  javascript?: string;
  files?: PlaygroundFile[];
  integrationNotes?: string;
  playgroundType: string;
  sandboxType: string;
}

/**
 * Configuration for a code playground request
 */
export interface CodePlaygroundRequest {
  projectDir: string;
  idea: string;
  playgroundType: PlaygroundType;
  sandboxType: SandboxType;
  model?: string;
  thinkingLevel?: string;
}

/**
 * Service for AI-powered code playground generation
 *
 * Spawns the Python code_playground_runner.py process and streams output
 * back to the renderer via events.
 *
 * Events emitted:
 * - 'status' (status: string) — Status update message
 * - 'stream-chunk' (chunk: string) — Streaming text output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: PlaygroundResult) — Playground generation complete with structured result
 */
export class CodePlaygroundService extends EventEmitter {
  private activeProcess: ChildProcess | null = null;
  private pythonPath: string = 'python';
  private autoBuildSourcePath: string | null = null;

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
      const runnerPath = path.join(p, 'runners', 'code_playground_runner.py');
      if (existsSync(runnerPath)) {
        this.autoBuildSourcePath = p;
        return p;
      }
    }

    return null;
  }

  /**
   * Cancel any active playground generation
   */
  cancel(): boolean {
    if (!this.activeProcess) return false;
    this.activeProcess.kill();
    this.activeProcess = null;
    return true;
  }

  /**
   * Generate code playground
   */
  async generate(request: CodePlaygroundRequest): Promise<void> {
    // Cancel any existing process
    this.cancel();

    const autoBuildSource = this.getAutoBuildSourcePath();
    if (!autoBuildSource) {
      this.emit('error', 'WorkPilot AI source not found. Cannot locate code_playground_runner.py');
      return;
    }

    const runnerPath = path.join(autoBuildSource, 'runners', 'code_playground_runner.py');
    if (!existsSync(runnerPath)) {
      this.emit('error', 'code_playground_runner.py not found in auto-claude directory');
      return;
    }

    // Emit initial status
    this.emit('status', 'Creating playground environment...');

    // Build command arguments
    const args = [
      runnerPath,
      '--project-dir', request.projectDir,
      '--idea', request.idea,
      '--playground-type', request.playgroundType,
      '--sandbox-type', request.sandboxType,
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
        const { readFileSync } = require('node:fs');
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
    let playgroundResult: PlaygroundResult | null = null;

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      const lines = text.split('\n');

      for (const line of lines) {
        // Check for the structured result marker
        if (line.startsWith('__PLAYGROUND_RESULT__:')) {
          try {
            const jsonStr = line.substring('__PLAYGROUND_RESULT__:'.length);
            playgroundResult = JSON.parse(jsonStr);
            this.emit('status', 'Playground ready');
          } catch (parseErr) {
            console.error('[CodePlayground] Failed to parse result:', parseErr);
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
      console.error('[CodePlayground]', text);
    });

    proc.on('close', (code) => {
      this.activeProcess = null;

      if (code === 0 && playgroundResult) {
        this.emit('complete', playgroundResult);
      } else if (code === 0) {
        // Process completed but no structured result found
        // Try to use the raw output as HTML content
        if (fullOutput.trim()) {
          this.emit('complete', {
            html: fullOutput.trim(),
            playgroundType: request.playgroundType,
            sandboxType: request.sandboxType,
            integrationNotes: 'Basic HTML playground generated from raw output.',
          } as PlaygroundResult);
        } else {
          this.emit('error', 'Playground generation completed but produced no output.');
        }
      } else {
        // Check for common error patterns
        const combinedOutput = fullOutput + stderrOutput;
        if (combinedOutput.includes('rate_limit') || combinedOutput.includes('Rate limit')) {
          this.emit('error', 'Rate limit reached. Please try again in a few moments.');
        } else if (combinedOutput.includes('authentication') || combinedOutput.includes('CLAUDE_OAUTH_TOKEN')) {
          this.emit('error', 'Authentication error. Please check your Claude credentials in Settings.');
        } else {
          this.emit('error', `Playground generation failed (exit code ${code}). ${stderrOutput.slice(-500)}`);
        }
      }
    });

    proc.on('error', (err) => {
      this.activeProcess = null;
      this.emit('error', `Failed to start playground generator: ${err.message}`);
    });
  }
}

// Singleton instance
export const codePlaygroundService = new CodePlaygroundService();
