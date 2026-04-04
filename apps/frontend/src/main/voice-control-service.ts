import { type ChildProcess, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import { existsSync } from "node:fs";
import path from "node:path";
import { app } from "electron";
import { MODEL_ID_MAP } from "../shared/constants";
import type { AppSettings } from "../shared/types";

/**
 * Result of voice command processing
 */
export interface VoiceControlResult {
	transcript: string;
	command: string;
	action: string;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
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
	private pythonPath: string = "python";
	private autoBuildSourcePath: string | null = null;
	private isRecording: boolean = false;

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
		const appPath = app.getAppPath(); // apps/frontend/ in dev, app.asar root in prod
		const possiblePaths = [
			path.join(appPath, "..", "backend"), // dev: apps/backend
			path.join(appPath, "..", "..", "apps", "backend"), // prod unpacked: resources/apps/backend
			path.join(__dirname, "..", "..", "..", "apps", "backend"), // dev out/main → apps/backend
			path.join(__dirname, "..", "..", "backend"), // alt build layout
			path.join(process.cwd(), "apps", "backend"),
			path.join(process.cwd(), "..", "backend"),
			path.join(app.getPath("userData"), "..", "auto-claude"),
		];

		for (const p of possiblePaths) {
			const runnerPath = path.join(p, "runners", "voice_control_runner.py");
			if (existsSync(runnerPath)) {
				this.autoBuildSourcePath = p;
				return p;
			}
		}

		console.error(
			"[VoiceControl] Runner not found. appPath:",
			appPath,
			"__dirname:",
			__dirname,
			"cwd:",
			process.cwd(),
		);
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
			this.emit(
				"error",
				"WorkPilot AI source not found. Cannot locate voice_control_runner.py",
			);
			return;
		}

		const runnerPath = path.join(
			autoBuildSource,
			"runners",
			"voice_control_runner.py",
		);
		if (!existsSync(runnerPath)) {
			this.emit(
				"error",
				"voice_control_runner.py not found in auto-claude directory",
			);
			return;
		}

		this.isRecording = true;

		// Emit initial status
		this.emit("status", "Starting voice recording...");

		const args = this.buildCommandArgs(request, runnerPath);
		const processEnv = this.buildProcessEnvironment();
		const proc = spawn(this.pythonPath, args, {
			cwd: autoBuildSource,
			env: processEnv,
		});

		this.activeProcess = proc;
		this.setupProcessHandlers(proc);
	}

	/**
	 * Build command arguments for the voice control process
	 */
	private buildCommandArgs(
		request: VoiceControlRequest,
		runnerPath: string,
	): string[] {
		const args = [runnerPath, "record"];

		if (request.projectDir) {
			args.push("--project-dir", request.projectDir);
		}
		if (request.language) {
			args.push("--language", request.language);
		}
		if (request.model) {
			const modelId = MODEL_ID_MAP[request.model] || request.model;
			args.push("--model", modelId);
		}
		if (request.thinkingLevel) {
			args.push("--thinking-level", request.thinkingLevel);
		}

		return args;
	}

	/**
	 * Build process environment with OAuth tokens
	 */
	private buildProcessEnvironment(): Record<string, string> {
		const processEnv: Record<string, string> = {
			...(process.env as Record<string, string>),
		};

		try {
			const settingsPath = path.join(app.getPath("userData"), "settings.json");
			if (existsSync(settingsPath)) {
				const { readFileSync } = require("node:fs");
				const settings: AppSettings = JSON.parse(
					readFileSync(settingsPath, "utf-8"),
				);
				if (settings.globalClaudeOAuthToken) {
					processEnv.CLAUDE_CODE_OAUTH_TOKEN = settings.globalClaudeOAuthToken;
				}
				if (settings.globalAnthropicApiKey) {
					processEnv.ANTHROPIC_API_KEY = settings.globalAnthropicApiKey;
				}
			}
		} catch {
			// Ignore settings read errors
		}

		return processEnv;
	}

	/**
	 * Setup event handlers for the voice control process
	 */
	private setupProcessHandlers(proc: ChildProcess): void {
		const outputState = {
			fullOutput: "",
			stderrOutput: "",
			voiceResult: null as VoiceControlResult | null,
		};

		proc.stdout?.on("data", (data: Buffer) => {
			const text = data.toString("utf-8");
			const lines = text.split("\n");

			for (const line of lines) {
				this.processOutputLine(line, outputState);
			}
		});

		proc.stderr?.on("data", (data: Buffer) => {
			const text = data.toString("utf-8");
			outputState.stderrOutput = (outputState.stderrOutput + text).slice(-5000);
			console.error("[VoiceControl]", text);
		});

		proc.on("close", (code) => {
			this.handleProcessClose(code, outputState);
		});

		proc.on("error", (err) => {
			this.activeProcess = null;
			this.isRecording = false;
			this.emit("error", `Failed to start voice control: ${err.message}`);
		});
	}

	/**
	 * Process a single line of output from the voice control process
	 */
	private processOutputLine(
		line: string,
		outputState: {
			fullOutput: string;
			stderrOutput: string;
			voiceResult: VoiceControlResult | null;
		},
	): void {
		if (line.startsWith("__VOICE_RESULT__:")) {
			this.handleVoiceResult(line, outputState);
		} else if (line.startsWith("__AUDIO_LEVEL__:")) {
			this.handleAudioLevel(line);
		} else if (line.startsWith("__DURATION__:")) {
			this.handleDuration(line);
		} else if (line.startsWith("__TOOL_START__:")) {
			this.handleToolStart(line);
		} else if (line.startsWith("__TOOL_END__:")) {
			// Tool completed, continue
		} else if (
			line.trim() &&
			!line.startsWith("INFO:") &&
			!line.startsWith("WARNING:") &&
			!line.startsWith("DEBUG:")
		) {
			outputState.fullOutput += line + "\n";
			this.emit("stream-chunk", line + "\n");
		}
	}

	/**
	 * Handle voice result from process output
	 */
	private handleVoiceResult(
		line: string,
		outputState: {
			fullOutput: string;
			stderrOutput: string;
			voiceResult: VoiceControlResult | null;
		},
	): void {
		try {
			const jsonStr = line.substring("__VOICE_RESULT__:".length);
			outputState.voiceResult = JSON.parse(jsonStr);
			this.emit("status", "Voice command processed");
		} catch (parseErr) {
			console.error("[VoiceControl] Failed to parse result:", parseErr);
		}
	}

	/**
	 * Handle audio level updates
	 */
	private handleAudioLevel(line: string): void {
		try {
			const level = Number.parseFloat(
				line.substring("__AUDIO_LEVEL__:".length),
			);
			this.emit("audio-level", Math.max(0, Math.min(1, level)));
		} catch {
			// Ignore parse errors for audio level
		}
	}

	/**
	 * Handle duration updates
	 */
	private handleDuration(line: string): void {
		try {
			const duration = Number.parseFloat(
				line.substring("__DURATION__:".length),
			);
			this.emit("duration", duration);
		} catch {
			// Ignore parse errors for duration
		}
	}

	/**
	 * Handle tool start notifications
	 */
	private handleToolStart(line: string): void {
		try {
			const toolInfo = JSON.parse(line.substring("__TOOL_START__:".length));
			this.emit("status", `Using ${toolInfo.tool}...`);
		} catch {
			// Ignore parse errors for tool notifications
		}
	}

	/**
	 * Handle process close event
	 */
	private handleProcessClose(
		code: number | null,
		outputState: {
			fullOutput: string;
			stderrOutput: string;
			voiceResult: VoiceControlResult | null;
		},
	): void {
		this.activeProcess = null;
		this.isRecording = false;

		if (code === 0 && outputState.voiceResult) {
			this.emit("complete", outputState.voiceResult);
		} else if (code !== 0) {
			this.handleProcessError(
				outputState.fullOutput,
				outputState.stderrOutput,
				code,
			);
		} else if (outputState.fullOutput.trim()) {
			this.handleRawOutputFallback(outputState.fullOutput);
		} else {
			this.emit("error", "Voice processing completed but produced no output.");
		}
	}

	/**
	 * Handle process errors with detailed error patterns
	 */
	private handleProcessError(
		fullOutput: string,
		stderrOutput: string,
		code: number | null,
	): void {
		const combinedOutput = fullOutput + stderrOutput;
		if (
			combinedOutput.includes("rate_limit") ||
			combinedOutput.includes("Rate limit")
		) {
			this.emit(
				"error",
				"Rate limit reached. Please try again in a few moments.",
			);
		} else if (
			combinedOutput.includes("authentication") ||
			combinedOutput.includes("CLAUDE_OAUTH_TOKEN")
		) {
			this.emit(
				"error",
				"Authentication error. Please check your Claude credentials in Settings.",
			);
		} else if (
			combinedOutput.includes("microphone") ||
			combinedOutput.includes("audio device")
		) {
			this.emit(
				"error",
				"Microphone access error. Please check your audio device permissions.",
			);
		} else {
			this.emit(
				"error",
				`Voice processing failed (exit code ${code}). ${stderrOutput.slice(-500)}`,
			);
		}
	}

	/**
	 * Handle fallback to raw output when no structured result is available
	 */
	private handleRawOutputFallback(fullOutput: string): void {
		this.emit("complete", {
			transcript: fullOutput.trim(),
			command: fullOutput.trim(),
			action: "unknown",
			parameters: {},
			confidence: 0.5,
		} as VoiceControlResult);
	}

	/**
	 * Stop current recording
	 */
	stopRecording(): void {
		if (this.activeProcess && this.isRecording) {
			this.emit("status", "Stopping recording...");
			// Send SIGTERM to gracefully stop recording
			this.activeProcess.kill("SIGTERM");
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
