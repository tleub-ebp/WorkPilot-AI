import { type ChildProcess, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import { existsSync } from "node:fs";
import path from "node:path";
import { app } from "electron";
import type { AppSettings } from "../shared/types";

export type CiPlatform = "github" | "gitlab" | "circleci";

export interface PipelineGeneratorRequest {
	projectDir: string;
	platforms?: CiPlatform[];
	model?: string;
	thinkingLevel?: string;
	refresh?: boolean;
	writeToprojectDir?: boolean;
}

export interface DetectedStack {
	languages: string[];
	package_managers: string[];
	frameworks: string[];
	test_runners: string[];
	has_docker: boolean;
	has_docker_compose: boolean;
	existing_ci: string[];
	build_scripts: string[];
}

export interface PipelineGeneratorResult {
	status: string;
	pipelines: Record<CiPlatform, string>;
	saved_files: Record<CiPlatform, string>;
	stack: DetectedStack;
	platforms_generated: CiPlatform[];
}

/**
 * Service for AI-powered CI/CD pipeline generation.
 *
 * Events:
 * - 'status' (status: string) — Status update
 * - 'stream-chunk' (chunk: string) — Streaming text output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: PipelineGeneratorResult) — Generation complete
 */
export class PipelineGeneratorService extends EventEmitter {
	private activeProcess: ChildProcess | null = null;
	private pythonPath = "python";
	private autoBuildSourcePath: string | null = null;

	configure(pythonPath?: string, autoBuildSourcePath?: string): void {
		if (pythonPath) this.pythonPath = pythonPath;
		if (autoBuildSourcePath) this.autoBuildSourcePath = autoBuildSourcePath;
	}

	private getAutoBuildSourcePath(): string | null {
		if (this.autoBuildSourcePath) return this.autoBuildSourcePath;
		const possiblePaths = [
			path.join(app.getPath("userData"), "..", "auto-claude"),
			path.join(process.cwd(), "apps", "backend"),
		];
		for (const p of possiblePaths) {
			if (existsSync(path.join(p, "runners", "pipeline_generator_runner.py"))) {
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

	async generate(request: PipelineGeneratorRequest): Promise<void> {
		this.cancel();

		const sourcePath = this.getAutoBuildSourcePath();
		if (!sourcePath) {
			this.emit(
				"error",
				"WorkPilot AI source not found. Cannot locate pipeline_generator_runner.py",
			);
			return;
		}

		const runnerPath = path.join(
			sourcePath,
			"runners",
			"pipeline_generator_runner.py",
		);
		if (!existsSync(runnerPath)) {
			this.emit("error", "pipeline_generator_runner.py not found");
			return;
		}

		this.emit("status", "Analyzing project stack...");

		const platforms = request.platforms?.join(",") ?? "github,gitlab";

		const args = [
			runnerPath,
			"--project",
			request.projectDir,
			"--platforms",
			platforms,
		];

		if (request.model) args.push("--model", request.model);
		if (request.thinkingLevel)
			args.push("--thinking-level", request.thinkingLevel);
		if (request.refresh) args.push("--refresh");
		if (request.writeToprojectDir) args.push("--write-to-project");

		const env = this.buildProcessEnvironment();
		await this.executeProcess(args, env, sourcePath);
	}

	private buildProcessEnvironment(): Record<string, string> {
		const env: Record<string, string> = {
			...(process.env as Record<string, string>),
		};
		try {
			const settingsPath = path.join(app.getPath("userData"), "settings.json");
			if (existsSync(settingsPath)) {
				const { readFileSync } = require("node:fs");
				const settings: AppSettings = JSON.parse(
					readFileSync(settingsPath, "utf-8"),
				);
				if (settings.globalClaudeOAuthToken)
					env.CLAUDE_OAUTH_TOKEN = settings.globalClaudeOAuthToken;
				if (settings.globalAnthropicApiKey)
					env.ANTHROPIC_API_KEY = settings.globalAnthropicApiKey;
			}
		} catch {
			/* ignore */
		}
		return env;
	}

	private async executeProcess(
		args: string[],
		env: Record<string, string>,
		cwd: string,
	): Promise<void> {
		const proc = spawn(this.pythonPath, args, {
			cwd,
			env,
			stdio: ["pipe", "pipe", "pipe"],
		});
		this.activeProcess = proc;

		let stderrOutput = "";
		let result: PipelineGeneratorResult | null = null;

		proc.stdout?.on("data", (data: Buffer) => {
			const text = data.toString("utf-8");
			for (const line of text.split("\n")) {
				if (line.startsWith("__PIPELINE_GENERATOR_RESULT__:")) {
					try {
						result = JSON.parse(
							line.substring("__PIPELINE_GENERATOR_RESULT__:".length),
						);
					} catch {
						/* ignore */
					}
				} else if (line.trim()) {
					this.emit("stream-chunk", `${line}\n`);
					// Parse status lines for UI feedback
					if (line.includes("Analyzing project")) {
						this.emit("status", "Analyzing project stack...");
					} else if (line.includes("Generating pipelines")) {
						this.emit("status", "Generating CI/CD pipelines with AI...");
					} else if (
						line.includes("✅") &&
						line.includes("pipeline generated")
					) {
						this.emit("status", line.trim());
					} else if (line.includes("Saved:")) {
						this.emit("status", "Saving generated pipelines...");
					}
				}
			}
		});

		proc.stderr?.on("data", (data: Buffer) => {
			stderrOutput = (stderrOutput + data.toString("utf-8")).slice(-5000);
			console.error("[PipelineGenerator]", data.toString("utf-8"));
		});

		proc.on("close", (code) => {
			this.activeProcess = null;
			if (code === 0 && result) {
				this.emit("complete", result);
			} else {
				this.emit(
					"error",
					`Pipeline generation failed (exit code ${code}). ${stderrOutput.slice(-500)}`,
				);
			}
		});

		proc.on("error", (err) => {
			this.activeProcess = null;
			this.emit("error", `Failed to start pipeline generator: ${err.message}`);
		});
	}
}

export const pipelineGeneratorService = new PipelineGeneratorService();
