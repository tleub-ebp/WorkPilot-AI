import { type ChildProcess, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import { existsSync } from "node:fs";
import path from "node:path";
import { app } from "electron";
import { MODEL_ID_MAP } from "../shared/constants";
import type { AppSettings } from "../shared/types";

export interface CodeMigrationResult {
	status: string;
	migration_description: string;
	dry_run: boolean;
	plan: {
		migration_id: string;
		description: string;
		source?: string;
		target?: string;
		note?: string;
	};
	execution: {
		status: string;
		files_modified?: number;
		note?: string;
	};
	summary: {
		migration_id: string;
		description: string;
		dry_run: boolean;
		plan_status: string;
		execution_status: string;
		files_modified: number;
	};
}

export interface CodeMigrationRequest {
	projectDir: string;
	migrationDescription: string;
	model?: string;
	thinkingLevel?: string;
	dryRun?: boolean;
	batchSize?: number;
}

/**
 * Service for AI-powered code migrations.
 *
 * Events:
 * - 'status' (status: string) — Status update
 * - 'stream-chunk' (chunk: string) — Streaming text output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: CodeMigrationResult) — Migration complete
 * - 'task-progress' (progress: { current: number; total: number; file: string }) — Task progress
 */
export class CodeMigrationService extends EventEmitter {
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
			if (existsSync(path.join(p, "runners", "code_migration_runner.py"))) {
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

	async startMigration(request: CodeMigrationRequest): Promise<void> {
		this.cancel();
		const sourcePath = this.getAutoBuildSourcePath();
		if (!sourcePath) {
			this.emit(
				"error",
				"WorkPilot AI source not found. Cannot locate code_migration_runner.py",
			);
			return;
		}
		const runnerPath = path.join(
			sourcePath,
			"runners",
			"code_migration_runner.py",
		);
		if (!existsSync(runnerPath)) {
			this.emit("error", "code_migration_runner.py not found");
			return;
		}

		this.emit("status", "Initializing Code Migration Agent...");

		const args = [
			runnerPath,
			"--project-dir",
			request.projectDir,
			"--migration-description",
			request.migrationDescription,
		];
		if (request.model) {
			args.push("--model", MODEL_ID_MAP[request.model] || request.model);
		}
		if (request.thinkingLevel)
			args.push("--thinking-level", request.thinkingLevel);
		if (request.dryRun) args.push("--dry-run");
		if (request.batchSize) args.push("--batch-size", String(request.batchSize));

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

		let fullOutput = "";
		let stderrOutput = "";
		let result: CodeMigrationResult | null = null;

		proc.stdout?.on("data", (data: Buffer) => {
			const text = data.toString("utf-8");
			for (const line of text.split("\n")) {
				if (line.startsWith("__MIGRATION_RESULT__:")) {
					try {
						result = JSON.parse(line.substring("__MIGRATION_RESULT__:".length));
						this.emit("status", "Migration complete");
					} catch {
						/* ignore */
					}
				} else if (line.startsWith("__TASK_PROGRESS__:")) {
					try {
						const progress = JSON.parse(
							line.substring("__TASK_PROGRESS__:".length),
						);
						this.emit("task-progress", progress);
					} catch {
						/* ignore */
					}
				} else if (line.trim()) {
					fullOutput += line + "\n";
					this.emit("stream-chunk", line + "\n");
					if (line.includes("Phase")) {
						this.emit("status", line.replace(/^\s*[\d.]+\s*/, "").trim());
					}
				}
			}
		});

		proc.stderr?.on("data", (data: Buffer) => {
			stderrOutput = (stderrOutput + data.toString("utf-8")).slice(-5000);
			console.error("[CodeMigration]", data.toString("utf-8"));
		});

		proc.on("close", (code) => {
			this.activeProcess = null;
			if (code === 0 && result) {
				this.emit("complete", result);
			} else if (code === 0 && fullOutput.trim()) {
				this.emit("complete", {
					status: "success",
					migration_description: "",
					dry_run: false,
					plan: {},
					execution: {},
					summary: { files_modified: 0 },
				});
			} else {
				const combined = fullOutput + stderrOutput;
				if (combined.includes("rate_limit")) {
					this.emit(
						"error",
						"Rate limit reached. Please try again in a few moments.",
					);
				} else {
					this.emit(
						"error",
						`Migration failed (exit code ${code}). ${stderrOutput.slice(-500)}`,
					);
				}
			}
		});

		proc.on("error", (err) => {
			this.activeProcess = null;
			this.emit("error", `Failed to start code migration: ${err.message}`);
		});
	}
}

export const codeMigrationService = new CodeMigrationService();
