import { type ChildProcess, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import { existsSync } from "node:fs";
import path from "node:path";
import { app } from "electron";
import { MODEL_ID_MAP } from "../shared/constants";
import type { AppSettings } from "../shared/types";

export interface DocumentationAgentResult {
	status: string;
	doc_types_processed: string[];
	generated_files: string[];
	results_by_type: Record<
		string,
		{
			status: string;
			file?: string;
			error?: string;
			endpoints_found?: number;
			inserted?: number;
		}
	>;
	coverage_before: {
		total_functions: number;
		documented_functions: number;
		total_classes: number;
		documented_classes: number;
		coverage_percent: number;
		missing_docs: string[];
	};
	coverage_after: {
		total_functions: number;
		documented_functions: number;
		total_classes: number;
		documented_classes: number;
		coverage_percent: number;
		missing_docs: string[];
	};
	outdated_found: number;
	summary: {
		files_written: number;
		coverage_before: string;
		coverage_after: string;
		coverage_delta: string;
		missing_docs_before: number;
		missing_docs_after: number;
	};
}

export interface DocumentationAgentRequest {
	projectDir: string;
	docTypes?: string[];
	outputDir?: string;
	insertInline?: boolean;
	model?: string;
	thinkingLevel?: string;
}

/**
 * Service for AI-powered documentation generation.
 *
 * Events:
 * - 'status' (status: string) — Status update
 * - 'stream-chunk' (chunk: string) — Streaming output
 * - 'error' (error: string) — Error message
 * - 'complete' (result: DocumentationAgentResult) — Generation complete
 */
export class DocumentationAgentService extends EventEmitter {
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
			if (
				existsSync(path.join(p, "runners", "documentation_agent_runner.py"))
			) {
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

	async generateDocs(request: DocumentationAgentRequest): Promise<void> {
		this.cancel();
		const sourcePath = this.getAutoBuildSourcePath();
		if (!sourcePath) {
			this.emit(
				"error",
				"WorkPilot AI source not found. Cannot locate documentation_agent_runner.py",
			);
			return;
		}
		const runnerPath = path.join(
			sourcePath,
			"runners",
			"documentation_agent_runner.py",
		);
		if (!existsSync(runnerPath)) {
			this.emit("error", "documentation_agent_runner.py not found");
			return;
		}

		this.emit("status", "Initializing Documentation Agent...");

		const args = [runnerPath, "--project-dir", request.projectDir];
		if (request.docTypes?.length)
			args.push("--doc-types", request.docTypes.join(","));
		if (request.outputDir) args.push("--output-dir", request.outputDir);
		if (request.insertInline) args.push("--insert-inline");
		if (request.model)
			args.push("--model", MODEL_ID_MAP[request.model] || request.model);
		if (request.thinkingLevel)
			args.push("--thinking-level", request.thinkingLevel);

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
		let result: DocumentationAgentResult | null = null;

		proc.stdout?.on("data", (data: Buffer) => {
			for (const line of data.toString("utf-8").split("\n")) {
				if (line.startsWith("__DOC_RESULT__:")) {
					try {
						result = JSON.parse(line.substring("__DOC_RESULT__:".length));
						this.emit("status", "Documentation complete");
					} catch {
						/* ignore */
					}
				} else if (line.trim()) {
					fullOutput += `${line}\n`;
					this.emit("stream-chunk", `${line}\n`);
					if (line.includes("Phase")) this.emit("status", line.trim());
				}
			}
		});

		proc.stderr?.on("data", (data: Buffer) => {
			stderrOutput = (stderrOutput + data.toString("utf-8")).slice(-5000);
			console.error("[DocAgent]", data.toString("utf-8"));
		});

		proc.on("close", (code) => {
			this.activeProcess = null;
			if (code === 0 && result) {
				this.emit("complete", result);
			} else if (code === 0 && fullOutput.trim()) {
				this.emit("complete", {
					status: "success",
					doc_types_processed: [],
					generated_files: [],
					results_by_type: {},
					coverage_before: { coverage_percent: 0 },
					coverage_after: { coverage_percent: 0 },
					outdated_found: 0,
					summary: {},
				});
			} else {
				this.emit(
					"error",
					`Documentation generation failed (exit code ${code}). ${stderrOutput.slice(-500)}`,
				);
			}
		});

		proc.on("error", (err) => {
			this.activeProcess = null;
			this.emit("error", `Failed to start documentation agent: ${err.message}`);
		});
	}
}

export const documentationAgentService = new DocumentationAgentService();
