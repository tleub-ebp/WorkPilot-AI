import { type ChildProcess, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import { existsSync } from "node:fs";
import path from "node:path";
import { app } from "electron";
import { MODEL_ID_MAP } from "../shared/constants";
import type { AppSettings } from "../shared/types";

/**
 * Request configuration for a context mesh operation
 */
export interface ContextMeshRequest {
	command:
		| "analyze"
		| "register"
		| "unregister"
		| "summary"
		| "recommendations";
	projectDir?: string;
	phase?: string;
	model?: string;
	thinkingLevel?: string;
}

/**
 * Service for Context Mesh — Cross-Project Intelligence
 *
 * Spawns the Python context_mesh_runner.py process and streams output
 * back to the renderer via events.
 *
 * Events emitted:
 * - 'status' (status: string) — Status update message
 * - 'stream-chunk' (chunk: string) — Streaming text output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: object) — Operation complete with data
 */
export class ContextMeshService extends EventEmitter {
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

		const validatePath = (p: string): boolean =>
			existsSync(path.join(p, "runners", "context_mesh_runner.py"));

		const possiblePaths = [
			...(app.isPackaged ? [path.join(process.resourcesPath, "backend")] : []),
			path.resolve(__dirname, "..", "..", "..", "backend"),
			path.resolve(app.getAppPath(), "..", "backend"),
			path.resolve(process.cwd(), "apps", "backend"),
		];

		for (const p of possiblePaths) {
			if (validatePath(p)) {
				this.autoBuildSourcePath = p;
				return p;
			}
		}

		return null;
	}

	/**
	 * Cancel any active operation
	 */
	cancel(): boolean {
		if (!this.activeProcess) return false;
		this.activeProcess.kill();
		this.activeProcess = null;
		return true;
	}

	/**
	 * Run a context mesh operation
	 */
	async execute(request: ContextMeshRequest): Promise<void> {
		this.cancel();

		const autoBuildSource = this.getAutoBuildSourcePath();
		if (!autoBuildSource) {
			this.emit(
				"error",
				"WorkPilot AI source not found. Cannot locate context_mesh_runner.py",
			);
			return;
		}

		const runnerPath = path.join(
			autoBuildSource,
			"runners",
			"context_mesh_runner.py",
		);
		if (!existsSync(runnerPath)) {
			this.emit("error", "context_mesh_runner.py not found");
			return;
		}

		this.emit("status", `Running context mesh: ${request.command}...`);

		const args = this.buildCommandArgs(request, runnerPath);
		const processEnv = this.buildProcessEnvironment();

		await this.executeProcess(args, processEnv, autoBuildSource);
	}

	private buildCommandArgs(
		request: ContextMeshRequest,
		runnerPath: string,
	): string[] {
		const args = [runnerPath, request.command];

		if (
			request.projectDir &&
			["register", "unregister", "recommendations"].includes(request.command)
		) {
			args.push("--project-dir", request.projectDir);
		}
		if (request.command === "analyze") {
			if (request.model) {
				const modelId = MODEL_ID_MAP[request.model] || request.model;
				args.push("--model", modelId);
			}
			if (request.thinkingLevel) {
				args.push("--thinking-level", request.thinkingLevel);
			}
		}
		if (request.phase && request.command === "recommendations") {
			args.push("--phase", request.phase);
		}

		return args;
	}

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
					processEnv.CLAUDE_OAUTH_TOKEN = settings.globalClaudeOAuthToken;
				}
				if (settings.globalAnthropicApiKey) {
					processEnv.ANTHROPIC_API_KEY = settings.globalAnthropicApiKey;
				}
				if (settings.globalOpenAIApiKey) {
					processEnv.OPENAI_API_KEY = settings.globalOpenAIApiKey;
				}
				if (settings.globalGoogleApiKey) {
					processEnv.GOOGLE_API_KEY = settings.globalGoogleApiKey;
				}
				if (settings.globalOpenRouterApiKey) {
					processEnv.OPENROUTER_API_KEY = settings.globalOpenRouterApiKey;
				}
				if (settings.globalGroqApiKey) {
					processEnv.GROQ_API_KEY = settings.globalGroqApiKey;
				}
				if (settings.globalMistralApiKey) {
					processEnv.MISTRAL_API_KEY = settings.globalMistralApiKey;
				}
				if (settings.globalDeepSeekApiKey) {
					processEnv.DEEPSEEK_API_KEY = settings.globalDeepSeekApiKey;
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
		const proc = spawn(this.pythonPath, args, {
			cwd,
			env: processEnv,
			stdio: ["pipe", "pipe", "pipe"],
		});

		this.activeProcess = proc;

		const processor = new ContextMeshOutputProcessor();

		proc.stdout?.on("data", (data: Buffer) => {
			processor.processStdout(data.toString("utf-8"), this);
		});

		proc.stderr?.on("data", (data: Buffer) => {
			processor.stderrOutput += data.toString("utf-8");
		});

		proc.on("close", (code) => {
			this.activeProcess = null;
			if (code === 0 && processor.completeResult) {
				this.emit("complete", processor.completeResult);
			} else if (code && code > 0) {
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
						"Authentication error. Please check your credentials in Settings.",
					);
				} else {
					this.emit(
						"error",
						`Context mesh operation failed (exit code ${code}). ${processor.stderrOutput.slice(-500)}`,
					);
				}
			} else {
				this.emit(
					"error",
					"Context mesh operation completed but produced no output.",
				);
			}
		});

		proc.on("error", (err) => {
			this.activeProcess = null;
			this.emit(
				"error",
				`Failed to start context mesh operation: ${err.message}`,
			);
		});
	}
}

class ContextMeshOutputProcessor {
	fullOutput = "";
	stderrOutput = "";
	// biome-ignore lint/suspicious/noExplicitAny: Runner output varies by command
	completeResult: any = null;

	processStdout(text: string, emitter: ContextMeshService): void {
		const lines = text.split("\n");

		for (const line of lines) {
			if (line.startsWith("CONTEXT_MESH_EVENT:")) {
				this.handleEvent(line, emitter);
			} else if (line.trim()) {
				this.fullOutput += `${line}\n`;
				emitter.emit("stream-chunk", `${line}\n`);
			}
		}
	}

	private handleEvent(line: string, emitter: ContextMeshService): void {
		try {
			const jsonStr = line.substring("CONTEXT_MESH_EVENT:".length);
			const event = JSON.parse(jsonStr);

			switch (event.type) {
				case "status":
					emitter.emit("status", event.message);
					break;
				case "stream_chunk":
					emitter.emit("stream-chunk", event.data);
					break;
				case "complete":
					this.completeResult = event.data;
					break;
				case "error":
					emitter.emit("error", event.message);
					break;
			}
		} catch {
			this.fullOutput += `${line}\n`;
		}
	}
}

// Singleton instance
export const contextMeshService = new ContextMeshService();
