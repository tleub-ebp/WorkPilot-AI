import { type ChildProcess, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import { existsSync } from "node:fs";
import path from "node:path";
import { app } from "electron";
import { MODEL_ID_MAP } from "../shared/constants";
import type { AppSettings } from "../shared/types";

/**
 * Result of auto-refactor analysis
 */
export interface AutoRefactorResult {
	analysis: {
		status: string;
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		analysis: any;
		files_analyzed: number;
	};
	plan: {
		status: string;
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		plan: any;
	};
	execution: {
		status: string;
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
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
	private pythonPath: string = "python";
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
			path.join(app.getPath("userData"), "..", "auto-claude"),
			path.join(process.cwd(), "apps", "backend"),
		];

		for (const p of possiblePaths) {
			const runnerPath = path.join(p, "runners", "auto_refactor_runner.py");
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
			this.emit(
				"error",
				"WorkPilot AI source not found. Cannot locate auto_refactor_runner.py",
			);
			return;
		}

		const runnerPath = path.join(
			autoBuildSource,
			"runners",
			"auto_refactor_runner.py",
		);
		if (!existsSync(runnerPath)) {
			this.emit(
				"error",
				"auto_refactor_runner.py not found in auto-claude directory",
			);
			return;
		}

		// Emit initial status
		this.emit("status", "Initializing Auto-Refactor Agent...");

		const args = this.buildCommandArgs(request, runnerPath);
		const processEnv = this.buildProcessEnvironment();

		await this.executeProcess(args, processEnv, autoBuildSource);
	}

	private buildCommandArgs(
		request: AutoRefactorRequest,
		runnerPath: string,
	): string[] {
		const args = [runnerPath, "--project-dir", request.projectDir];

		if (request.model) {
			const modelId = MODEL_ID_MAP[request.model] || request.model;
			args.push("--model", modelId);
		}
		if (request.thinkingLevel) {
			args.push("--thinking-level", request.thinkingLevel);
		}
		if (request.autoExecute) {
			args.push("--auto-execute");
		}

		return args;
	}

	private buildProcessEnvironment(): Record<string, string> {
		const processEnv: Record<string, string> = {
			...(process.env as Record<string, string>),
		};

		// Read OAuth token from settings if available
		try {
			const settingsPath = path.join(app.getPath("userData"), "settings.json");
			if (existsSync(settingsPath)) {
				const { readFileSync } = require("node:fs");
				const settings: AppSettings = JSON.parse(
					readFileSync(settingsPath, "utf-8"),
				);
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

		return processEnv;
	}

	private async executeProcess(
		args: string[],
		processEnv: Record<string, string>,
		cwd: string,
	): Promise<void> {
		// Spawn Python process
		const proc = spawn(this.pythonPath, args, {
			cwd,
			env: processEnv,
			stdio: ["pipe", "pipe", "pipe"],
		});

		this.activeProcess = proc;

		const processor = new OutputProcessor();

		this.setupProcessHandlers(proc, processor);
	}

	private setupProcessHandlers(
		proc: ChildProcess,
		processor: OutputProcessor,
	): void {
		proc.stdout?.on("data", (data: Buffer) => {
			processor.processStdout(data.toString("utf-8"), this);
		});

		proc.stderr?.on("data", (data: Buffer) => {
			processor.processStderr(data.toString("utf-8"));
		});

		proc.on("close", (code) => {
			this.activeProcess = null;
			this.handleProcessCompletion(code, processor);
		});

		proc.on("error", (err) => {
			this.activeProcess = null;
			this.emit("error", `Failed to start auto-refactor: ${err.message}`);
		});
	}

	private handleProcessCompletion(
		code: number | null,
		processor: OutputProcessor,
	): void {
		if (code === 0 && processor.analysisResult) {
			this.emit("complete", processor.analysisResult);
			if (processor.executionResult) {
				this.emit("execution-complete", processor.executionResult);
			}
		} else if (code && code > 0) {
			this.handleProcessError(code, processor);
		} else if (processor.fullOutput.trim()) {
			const fallbackResult = this.createFallbackResult(processor.fullOutput);
			this.emit("complete", fallbackResult);
		} else {
			this.emit("error", "Analysis completed but produced no output.");
		}
	}

	private handleProcessError(code: number, processor: OutputProcessor): void {
		const combinedOutput = processor.fullOutput + processor.stderrOutput;
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
		} else {
			this.emit(
				"error",
				`Analysis failed (exit code ${code}). ${processor.stderrOutput.slice(-500)}`,
			);
		}
	}

	private createFallbackResult(output: string): AutoRefactorResult {
		const trimmedOutput = output.trim();
		return {
			analysis: {
				status: "success",
				analysis: { raw_output: trimmedOutput },
				files_analyzed: 0,
			},
			plan: {
				status: "success",
				plan: { raw_output: trimmedOutput },
			},
			execution: {
				status: "success",
				execution: { raw_output: trimmedOutput },
				auto_executed: false,
			},
			summary: {
				issues_found: 0,
				files_analyzed: 0,
				refactoring_items: 0,
				quick_wins: 0,
				estimated_effort: "Unknown",
				risk_level: "Unknown",
			},
		};
	}
}

class OutputProcessor {
	fullOutput = "";
	stderrOutput = "";
	analysisResult: AutoRefactorResult | null = null;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	executionResult: any = null;

	processStdout(text: string, emitter: AutoRefactorService): void {
		const lines = text.split("\n");

		for (const line of lines) {
			this.processLine(line, emitter);
		}
	}

	private processLine(line: string, emitter: AutoRefactorService): void {
		if (line.startsWith("__AUTO_REFACTOR_RESULT__:")) {
			this.handleAnalysisResult(line, emitter);
		} else if (line.startsWith("__AUTO_REFACTOR_EXECUTION__:")) {
			this.handleExecutionResult(line, emitter);
		} else if (line.startsWith("__TOOL_START__:")) {
			this.handleToolStart(line, emitter);
		} else if (line.startsWith("__TOOL_END__:")) {
			// Tool completed, continue
		} else if (line.trim()) {
			this.fullOutput += line + "\n";
			emitter.emit("stream-chunk", line + "\n");
		}
	}

	private handleAnalysisResult(
		line: string,
		emitter: AutoRefactorService,
	): void {
		try {
			const jsonStr = line.substring("__AUTO_REFACTOR_RESULT__:".length);
			this.analysisResult = JSON.parse(jsonStr);
			emitter.emit("status", "Analysis complete");
		} catch (parseErr) {
			console.error(
				"[AutoRefactor] Failed to parse analysis result:",
				parseErr,
			);
		}
	}

	private handleExecutionResult(
		line: string,
		emitter: AutoRefactorService,
	): void {
		try {
			const jsonStr = line.substring("__AUTO_REFACTOR_EXECUTION__:".length);
			this.executionResult = JSON.parse(jsonStr);
			emitter.emit("status", "Execution complete");
		} catch (parseErr) {
			console.error(
				"[AutoRefactor] Failed to parse execution result:",
				parseErr,
			);
		}
	}

	private handleToolStart(line: string, emitter: AutoRefactorService): void {
		try {
			const toolInfo = JSON.parse(line.substring("__TOOL_START__:".length));
			emitter.emit("status", `Using ${toolInfo.tool}...`);
		} catch {
			// Ignore parse errors for tool notifications
		}
	}

	processStderr(text: string): void {
		this.stderrOutput = (this.stderrOutput + text).slice(-5000);
		console.error("[AutoRefactor]", text);
	}
}

// Singleton instance
export const autoRefactorService = new AutoRefactorService();
