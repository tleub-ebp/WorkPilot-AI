import { spawn, ChildProcess } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';
import { app } from 'electron';
import { MODEL_ID_MAP } from '../shared/constants';
import type { AppSettings } from '../shared/types';

/**
 * Result of voice command processing
 */
export interface VoiceControlResult {
  transcript: string;
  command: string;
  action: string;
  parameters: Record<string, any>;
  confidence: number;
}

/**
 * Configuration for voice control request
 */
export interface VoiceControlRequest {
  projectDir?: string;
  language?: string;
  model?: string;
  thinkingLevel?: string;
}

/**
 * Service for voice control with speech-to-text and command processing
 *
 * Manages audio recording, speech-to-text processing, and command interpretation.
 * Uses Python runner for Whisper/Deepgram integration and AI command processing.
 *
 * Events emitted:
 * - 'status' (status: string) — Status update message
 * - 'stream-chunk' (chunk: string) — Streaming text output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: VoiceControlResult) — Command processed with structured result
 * - 'audio-level' (level: number) — Audio level during recording (0-1)
 * - 'duration' (duration: number) — Recording duration in seconds
 */
export class VoiceControlService extends EventEmitter {
  private activeProcess: ChildProcess | null = null;
  private pythonPath: string = 'python';
  private autoBuildSourcePath: string | null = null;
  private isRecording: boolean = false;

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
      const runnerPath = path.join(p, 'runners', 'voice_control_runner.py');
      if (existsSync(runnerPath)) {
        this.autoBuildSourcePath = p;
        return p;
      }
    }

    return null;
  }

  /**
   * Cancel any active recording or processing
   */
  cancel(): boolean {
    if (!this.activeProcess) return false;
    this.activeProcess.kill();
    this.activeProcess = null;
    this.isRecording = false;
    return true;
  }

  /**
   * Start voice recording and processing
   */
  async startRecording(request: VoiceControlRequest = {}): Promise<void> {
    // Cancel any existing process
    this.cancel();

    const autoBuildSource = this.getAutoBuildSourcePath();
    if (!autoBuildSource) {
      this.emit('error', 'WorkPilot AI source not found. Cannot locate voice_control_runner.py');
      return;
    }

    const runnerPath = path.join(autoBuildSource, 'runners', 'voice_control_runner.py');
    if (!existsSync(runnerPath)) {
      this.emit('error', 'voice_control_runner.py not found in auto-claude directory');
      return;
    }

    this.isRecording = true;

    // Emit initial status
    this.emit('status', 'Starting voice recording...');

    // Build command arguments
    const args = [
      runnerPath,
      'record',
    ];

    // Add optional parameters
    if (request.projectDir) {
      args.push('--project-dir', request.projectDir);
    }
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
    let voiceResult: VoiceControlResult | null = null;

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      const lines = text.split('\n');

      for (const line of lines) {
        // Check for the structured result marker
        if (line.startsWith('__VOICE_RESULT__:')) {
          try {
            const jsonStr = line.substring('__VOICE_RESULT__:'.length);
            voiceResult = JSON.parse(jsonStr);
            this.emit('status', 'Voice command processed');
          } catch (parseErr) {
            console.error('[VoiceControl] Failed to parse result:', parseErr);
          }
        } else if (line.startsWith('__AUDIO_LEVEL__:')) {
          // Handle audio level updates during recording
          try {
            const level = parseFloat(line.substring('__AUDIO_LEVEL__:'.length));
            this.emit('audio-level', Math.max(0, Math.min(1, level)));
          } catch {
            // Ignore parse errors for audio level
          }
        } else if (line.startsWith('__DURATION__:')) {
          // Handle duration updates
          try {
            const duration = parseFloat(line.substring('__DURATION__:'.length));
            this.emit('duration', duration);
          } catch {
            // Ignore parse errors for duration
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
      console.error('[VoiceControl]', text);
    });

    proc.on('close', (code) => {
      this.activeProcess = null;
      this.isRecording = false;

      if (code === 0 && voiceResult) {
        this.emit('complete', voiceResult);
      } else if (code !== 0) {
        // Check for common error patterns
        const combinedOutput = fullOutput + stderrOutput;
        if (combinedOutput.includes('rate_limit') || combinedOutput.includes('Rate limit')) {
          this.emit('error', 'Rate limit reached. Please try again in a few moments.');
        } else if (combinedOutput.includes('authentication') || combinedOutput.includes('CLAUDE_OAUTH_TOKEN')) {
          this.emit('error', 'Authentication error. Please check your Claude credentials in Settings.');
        } else if (combinedOutput.includes('microphone') || combinedOutput.includes('audio device')) {
          this.emit('error', 'Microphone access error. Please check your audio device permissions.');
        } else {
          this.emit('error', `Voice processing failed (exit code ${code}). ${stderrOutput.slice(-500)}`);
        }
      } else {
        // Process completed but no structured result found
        // Try to use the raw output as the transcript
        if (fullOutput.trim()) {
          this.emit('complete', {
            transcript: fullOutput.trim(),
            command: fullOutput.trim(),
            action: 'unknown',
            parameters: {},
            confidence: 0.5,
          } as VoiceControlResult);
        } else {
          this.emit('error', 'Voice processing completed but produced no output.');
        }
      }
    });

    proc.on('error', (err) => {
      this.activeProcess = null;
      this.isRecording = false;
      this.emit('error', `Failed to start voice control: ${err.message}`);
    });
  }

  /**
   * Stop current recording
   */
  stopRecording(): void {
    if (this.activeProcess && this.isRecording) {
      this.emit('status', 'Stopping recording...');
      // Send SIGTERM to gracefully stop recording
      this.activeProcess.kill('SIGTERM');
    }
  }

  /**
   * Check if currently recording
   */
  isActive(): boolean {
    return this.isRecording || this.activeProcess !== null;
  }
}

// Singleton instance
export const voiceControlService = new VoiceControlService();
