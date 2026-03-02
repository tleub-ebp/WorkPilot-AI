import { spawn, ChildProcess } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';
import { app } from 'electron';
import { MODEL_ID_MAP } from '../shared/constants';
import type { AppSettings } from '../shared/types';

/**
 * Result of context-aware snippet generation
 */
export interface ContextAwareSnippetResult {
  snippet: string;
  language: string;
  description: string;
  context_used: string[];
  adaptations: string[];
  reasoning: string;
}

/**
 * Configuration for a context-aware snippet generation request
 */
export interface ContextAwareSnippetRequest {
  projectDir: string;
  snippetType: 'component' | 'function' | 'class' | 'hook' | 'utility' | 'api' | 'test';
  description: string;
  language?: string;
  model?: string;
  thinkingLevel?: string;
}

/**
 * Service for context-aware snippet generation
 *
 * Spawns the Python context_aware_snippets_runner.py process and streams output
 * back to the renderer via events.
 *
 * Events emitted:
 * - 'status' (status: string) — Status update message
 * - 'stream-chunk' (chunk: string) — Streaming text output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: ContextAwareSnippetResult) — Generation complete with structured result
 */
export class ContextAwareSnippetsService extends EventEmitter {
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
      const runnerPath = path.join(p, 'runners', 'context_aware_snippets_runner.py');
      if (existsSync(runnerPath)) {
        this.autoBuildSourcePath = p;
        return p;
      }
    }

    return null;
  }

  /**
   * Cancel any active generation
   */
  cancel(): boolean {
    if (!this.activeProcess) return false;
    this.activeProcess.kill();
    this.activeProcess = null;
    return true;
  }

  /**
   * Generate context-aware snippet
   */
  async generateSnippet(request: ContextAwareSnippetRequest): Promise<void> {
    // Cancel any existing process
    this.cancel();

    const autoBuildSource = this.getAutoBuildSourcePath();
    if (!autoBuildSource) {
      this.emit('error', 'WorkPilot AI source not found. Cannot locate context_aware_snippets_runner.py');
      return;
    }

    const runnerPath = path.join(autoBuildSource, 'runners', 'context_aware_snippets_runner.py');
    if (!existsSync(runnerPath)) {
      this.emit('error', 'context_aware_snippets_runner.py not found in auto-claude directory');
      return;
    }

    // Emit initial status
    this.emit('status', 'Analyzing project context and generating snippet...');

    // Build command arguments
    const args = [
      runnerPath,
      '--project-dir', request.projectDir,
      '--snippet-type', request.snippetType,
      '--description', request.description,
    ];

    // Add optional arguments
    if (request.language) {
      args.push('--language', request.language);
    }
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
    let snippetResult: ContextAwareSnippetResult | null = null;

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      const lines = text.split('\n');

      for (const line of lines) {
        // Check for the structured result marker
        if (line.startsWith('__CONTEXT_AWARE_SNIPPET__:')) {
          try {
            const jsonStr = line.substring('__CONTEXT_AWARE_SNIPPET__:'.length);
            snippetResult = JSON.parse(jsonStr);
            this.emit('status', 'Snippet generation complete');
          } catch (parseErr) {
            console.error('[ContextAwareSnippets] Failed to parse result:', parseErr);
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
      console.error('[ContextAwareSnippets]', text);
    });

    proc.on('close', (code) => {
      this.activeProcess = null;

      if (code === 0 && snippetResult) {
        this.emit('complete', snippetResult);
      } else if (code !== 0) {
        // Check for common error patterns
        const combinedOutput = fullOutput + stderrOutput;
        if (combinedOutput.includes('rate_limit') || combinedOutput.includes('Rate limit')) {
          this.emit('error', 'Rate limit reached. Please try again in a few moments.');
        } else if (combinedOutput.includes('authentication') || combinedOutput.includes('CLAUDE_OAUTH_TOKEN')) {
          this.emit('error', 'Authentication error. Please check your Claude credentials in Settings.');
        } else {
          this.emit('error', `Snippet generation failed (exit code ${code}). ${stderrOutput.slice(-500)}`);
        }
      } else {
        // Process completed but no structured result found
        // Try to use the raw output as the snippet
        if (fullOutput.trim()) {
          this.emit('complete', {
            snippet: fullOutput.trim(),
            language: request.language || 'unknown',
            description: request.description,
            context_used: ['raw-output'],
            adaptations: ['basic-formatting'],
            reasoning: 'The generator completed but did not produce a structured result.',
          } as ContextAwareSnippetResult);
        } else {
          this.emit('error', 'Snippet generation completed but produced no output.');
        }
      }
    });

    proc.on('error', (err) => {
      this.activeProcess = null;
      this.emit('error', `Failed to start snippet generator: ${err.message}`);
    });
  }
}

// Singleton instance
export const contextAwareSnippetsService = new ContextAwareSnippetsService();
