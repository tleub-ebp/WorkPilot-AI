import { type ChildProcess, execSync, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { app } from "electron";
import type { AppSettings } from "../shared/types";
import type {
	CompanionConfig,
	CompanionState,
	FileChangeEvent,
	LiveSuggestion,
	TakeoverProposal,
} from "../shared/types/live-companion";

const CONFIG_DIR = path.join(os.homedir(), ".workpilot", "live_companion");
const CONFIG_FILE = path.join(CONFIG_DIR, "config.json");
const SUGGESTIONS_FILE = path.join(CONFIG_DIR, "suggestions.json");
const TAKEOVERS_FILE = path.join(CONFIG_DIR, "takeovers.json");

const DEFAULT_CONFIG: CompanionConfig = {
	enabled: false,
	watch_debounce_ms: 1500,
	suggestion_enabled: true,
	takeover_enabled: true,
	takeover_inactivity_seconds: 120,
	min_suggestion_confidence: 0.5,
	max_suggestions_per_file: 5,
	watch_patterns: [
		"**/*.ts",
		"**/*.tsx",
		"**/*.js",
		"**/*.jsx",
		"**/*.py",
		"**/*.rs",
		"**/*.go",
		"**/*.java",
		"**/*.cs",
		"**/*.rb",
		"**/*.php",
		"**/*.vue",
		"**/*.svelte",
	],
	ignore_patterns: [
		"**/node_modules/**",
		"**/.git/**",
		"**/dist/**",
		"**/build/**",
		"**/__pycache__/**",
		"**/venv/**",
		"**/.venv/**",
		"**/*.min.js",
		"**/*.map",
	],
};

/**
 * Live Development Companion Service
 *
 * Manages file watching via chokidar, debounced AI analysis,
 * suggestion tracking, and takeover detection.
 *
 * Events emitted:
 * - 'state-changed' (state: CompanionState)
 * - 'suggestion' (suggestion: LiveSuggestion)
 * - 'takeover-proposal' (proposal: TakeoverProposal)
 * - 'file-change' (event: FileChangeEvent)
 * - 'error' (error: string)
 */
export class LiveCompanionService extends EventEmitter {
	private watcher: unknown = null; // chokidar FSWatcher
	private pythonPath: string = "python";
	private autoBuildSourcePath: string | null = null;
	private activeProcess: ChildProcess | null = null;
	private debounceTimer: ReturnType<typeof setTimeout> | null = null;
	private pendingChanges: FileChangeEvent[] = [];
	private takeoverCheckInterval: ReturnType<typeof setInterval> | null = null;
	private fileActivityMap: Map<
		string,
		{ lastChange: number; changeCount: number }
	> = new Map();

	private state: CompanionState = {
		active: false,
		watching_project: "",
		files_watched: 0,
		changes_detected: 0,
		suggestions_generated: 0,
		suggestions_accepted: 0,
		takeovers_proposed: 0,
		takeovers_accepted: 0,
		started_at: "",
		last_change_at: "",
	};

	/**
	 * Configure paths
	 */
	configure(pythonPath?: string, autoBuildSourcePath?: string): void {
		if (pythonPath) this.pythonPath = pythonPath;
		if (autoBuildSourcePath) this.autoBuildSourcePath = autoBuildSourcePath;
	}

	/**
	 * Get current companion state
	 */
	getState(): CompanionState {
		return { ...this.state };
	}

	/**
	 * Get companion config
	 */
	getConfig(): CompanionConfig {
		try {
			if (existsSync(CONFIG_FILE)) {
				return {
					...DEFAULT_CONFIG,
					...JSON.parse(readFileSync(CONFIG_FILE, "utf-8")),
				};
			}
		} catch {
			/* ignore */
		}
		return { ...DEFAULT_CONFIG };
	}

	/**
	 * Update companion config
	 */
	updateConfig(updates: Partial<CompanionConfig>): CompanionConfig {
		const config = { ...this.getConfig(), ...updates };
		mkdirSync(CONFIG_DIR, { recursive: true });
		writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), "utf-8");
		return config;
	}

	/**
	 * Start watching a project directory
	 */
	async start(projectDir: string): Promise<boolean> {
		if (this.state.active) {
			this.stop();
		}

		const config = this.getConfig();

		try {
			// Dynamic import of chokidar (available in Electron)
			const chokidar = require("chokidar");

			this.watcher = chokidar.watch(config.watch_patterns, {
				cwd: projectDir,
				ignored: config.ignore_patterns,
				persistent: true,
				ignoreInitial: true,
				awaitWriteFinish: {
					stabilityThreshold: 300,
					pollInterval: 100,
				},
			});

			const watcher = this.watcher as {
				on: (event: string, cb: (...args: unknown[]) => void) => void;
				getWatched: () => Record<string, string[]>;
				close: () => Promise<void>;
			};

			watcher.on("change", (filePath: string) => {
				this.handleFileChange(
					projectDir,
					filePath as string,
					"modified",
					config,
				);
			});

			watcher.on("add", (filePath: string) => {
				this.handleFileChange(
					projectDir,
					filePath as string,
					"created",
					config,
				);
			});

			watcher.on("unlink", (filePath: string) => {
				this.handleFileChange(
					projectDir,
					filePath as string,
					"deleted",
					config,
				);
			});

			// Start takeover check interval
			if (config.takeover_enabled) {
				this.takeoverCheckInterval = setInterval(() => {
					this.checkForTakeover(config);
				}, 30_000); // Check every 30s
			}

			// Update state
			this.state = {
				...this.state,
				active: true,
				watching_project: projectDir,
				started_at: new Date().toISOString(),
			};

			this.emit("state-changed", this.state);
			return true;
		} catch (error) {
			this.emit(
				"error",
				`Failed to start file watcher: ${(error as Error).message}`,
			);
			return false;
		}
	}

	/**
	 * Stop watching
	 */
	stop(): void {
		if (this.watcher) {
			(this.watcher as { close: () => Promise<void> }).close();
			this.watcher = null;
		}

		if (this.debounceTimer) {
			clearTimeout(this.debounceTimer);
			this.debounceTimer = null;
		}

		if (this.takeoverCheckInterval) {
			clearInterval(this.takeoverCheckInterval);
			this.takeoverCheckInterval = null;
		}

		if (this.activeProcess) {
			this.activeProcess.kill();
			this.activeProcess = null;
		}

		this.pendingChanges = [];
		this.fileActivityMap.clear();

		this.state = {
			...this.state,
			active: false,
		};

		this.emit("state-changed", this.state);
	}

	/**
	 * Get stored suggestions
	 */
	getSuggestions(): LiveSuggestion[] {
		try {
			if (existsSync(SUGGESTIONS_FILE)) {
				const data = JSON.parse(readFileSync(SUGGESTIONS_FILE, "utf-8"));
				return (data.suggestions || []).filter(
					(s: LiveSuggestion) => s.status === "active",
				);
			}
		} catch {
			/* ignore */
		}
		return [];
	}

	/**
	 * Dismiss a suggestion
	 */
	dismissSuggestion(suggestionId: string): boolean {
		return this.updateSuggestionStatus(suggestionId, "dismissed");
	}

	/**
	 * Mark a suggestion as applied
	 */
	applySuggestion(suggestionId: string): boolean {
		const result = this.updateSuggestionStatus(suggestionId, "applied");
		if (result) {
			this.state.suggestions_accepted++;
			this.emit("state-changed", this.state);
		}
		return result;
	}

	/**
	 * Get takeover proposals
	 */
	getTakeovers(): TakeoverProposal[] {
		try {
			if (existsSync(TAKEOVERS_FILE)) {
				const data = JSON.parse(readFileSync(TAKEOVERS_FILE, "utf-8"));
				return (data.takeovers || []).filter(
					(t: TakeoverProposal) => t.status === "proposed",
				);
			}
		} catch {
			/* ignore */
		}
		return [];
	}

	/**
	 * Accept a takeover proposal
	 */
	acceptTakeover(proposalId: string): boolean {
		const result = this.updateTakeoverStatus(proposalId, "accepted");
		if (result) {
			this.state.takeovers_accepted++;
			this.emit("state-changed", this.state);
		}
		return result;
	}

	/**
	 * Decline a takeover proposal
	 */
	declineTakeover(proposalId: string): boolean {
		return this.updateTakeoverStatus(proposalId, "declined");
	}

	// ── Private methods ──────────────────────────────────────────

	private handleFileChange(
		projectDir: string,
		filePath: string,
		changeType: string,
		config: CompanionConfig,
	): void {
		const fullPath = path.join(projectDir, filePath);

		// Track file activity for takeover detection
		const existing = this.fileActivityMap.get(fullPath) || {
			lastChange: 0,
			changeCount: 0,
		};
		this.fileActivityMap.set(fullPath, {
			lastChange: Date.now(),
			changeCount: existing.changeCount + 1,
		});

		this.state.changes_detected++;
		this.state.last_change_at = new Date().toISOString();

		// Get diff for modified files
		let diff = "";
		if (changeType === "modified") {
			try {
				diff = execSync(`git diff -- "${filePath}"`, {
					cwd: projectDir,
					encoding: "utf-8",
					timeout: 5000,
				}).slice(0, 4000);
			} catch {
				/* non-git or git error */
			}
		}

		const event: FileChangeEvent = {
			file_path: filePath,
			change_type: changeType as FileChangeEvent["change_type"],
			diff,
			language: this.detectLanguage(filePath),
			timestamp: new Date().toISOString(),
		};

		this.emit("file-change", event);

		if (!config.suggestion_enabled) return;

		// Debounced analysis
		this.pendingChanges.push(event);

		if (this.debounceTimer) {
			clearTimeout(this.debounceTimer);
		}

		this.debounceTimer = setTimeout(() => {
			this.analyzePendingChanges(projectDir);
		}, config.watch_debounce_ms);
	}

	private async analyzePendingChanges(projectDir: string): Promise<void> {
		if (this.pendingChanges.length === 0) return;
		if (this.activeProcess) return; // Don't overlap analyses

		const changes = [...this.pendingChanges];
		this.pendingChanges = [];

		const autoBuildSource = this.getAutoBuildSourcePath();
		if (!autoBuildSource) return;

		const runnerPath = path.join(
			autoBuildSource,
			"runners",
			"live_companion_runner.py",
		);
		if (!existsSync(runnerPath)) return;

		// Write changes to temp file for batch analysis
		const tmpFile = path.join(
			os.tmpdir(),
			`workpilot_companion_${Date.now()}.json`,
		);
		writeFileSync(
			tmpFile,
			JSON.stringify({
				changes: changes.map((c) => ({
					file_path: c.file_path,
					change_type: c.change_type,
					diff: c.diff,
					language: c.language,
					timestamp: c.timestamp,
				})),
			}),
			"utf-8",
		);

		const args = [
			runnerPath,
			"analyze-batch",
			"--project-dir",
			projectDir,
			"--changes-file",
			tmpFile,
		];

		const processEnv = this.buildProcessEnvironment();

		const proc = spawn(this.pythonPath, args, {
			cwd: autoBuildSource,
			env: processEnv,
			stdio: ["pipe", "pipe", "pipe"],
		});

		this.activeProcess = proc;

		let stdout = "";
		proc.stdout?.on("data", (data: Buffer) => {
			stdout += data.toString("utf-8");
		});

		proc.on("close", () => {
			this.activeProcess = null;

			// Clean up temp file
			try {
				require("node:fs").unlinkSync(tmpFile);
			} catch {
				/* ignore */
			}

			// Parse events from stdout
			for (const line of stdout.split("\n")) {
				if (line.startsWith("LIVE_COMPANION_EVENT:")) {
					try {
						const event = JSON.parse(
							line.substring("LIVE_COMPANION_EVENT:".length),
						);
						if (event.type === "complete" && event.data?.suggestions) {
							for (const suggestion of event.data.suggestions) {
								this.state.suggestions_generated++;
								this.storeSuggestion(suggestion);
								this.emit("suggestion", suggestion);
							}
							this.emit("state-changed", this.state);
						}
					} catch {
						/* ignore parse errors */
					}
				}
			}
		});

		proc.on("error", () => {
			this.activeProcess = null;
		});
	}

	private checkForTakeover(config: CompanionConfig): void {
		const now = Date.now();
		const thresholdMs = config.takeover_inactivity_seconds * 1000;

		for (const [filePath, activity] of this.fileActivityMap.entries()) {
			if (activity.changeCount < 3) continue; // Need min activity first
			const inactive = now - activity.lastChange;

			if (inactive >= thresholdMs) {
				const inactiveSeconds = Math.floor(inactive / 1000);
				const fileName = path.basename(filePath);

				const proposal: TakeoverProposal = {
					proposal_id: `tkv-${Date.now().toString(36)}`,
					file_path: filePath,
					reason: "inactivity",
					description: `You've been inactive on ${fileName} for ${Math.floor(inactiveSeconds / 60)}m${inactiveSeconds % 60}s after ${activity.changeCount} edits. Would you like AI to help?`,
					inactivity_seconds: inactiveSeconds,
					complexity_score: 0,
					status: "proposed",
					ai_plan: "",
					ai_result_summary: "",
					created_at: new Date().toISOString(),
				};

				this.storeTakeover(proposal);
				this.state.takeovers_proposed++;
				this.emit("takeover-proposal", proposal);
				this.emit("state-changed", this.state);

				// Don't re-propose for this file
				this.fileActivityMap.delete(filePath);
			}
		}
	}

	private storeSuggestion(suggestion: LiveSuggestion): void {
		try {
			mkdirSync(CONFIG_DIR, { recursive: true });
			const data = existsSync(SUGGESTIONS_FILE)
				? JSON.parse(readFileSync(SUGGESTIONS_FILE, "utf-8"))
				: { suggestions: [] };
			data.suggestions.push(suggestion);
			// Keep last 100 suggestions
			if (data.suggestions.length > 100) {
				data.suggestions = data.suggestions.slice(-100);
			}
			writeFileSync(SUGGESTIONS_FILE, JSON.stringify(data, null, 2), "utf-8");
		} catch {
			/* ignore */
		}
	}

	private storeTakeover(proposal: TakeoverProposal): void {
		try {
			mkdirSync(CONFIG_DIR, { recursive: true });
			const data = existsSync(TAKEOVERS_FILE)
				? JSON.parse(readFileSync(TAKEOVERS_FILE, "utf-8"))
				: { takeovers: [] };
			data.takeovers.push(proposal);
			if (data.takeovers.length > 50) {
				data.takeovers = data.takeovers.slice(-50);
			}
			writeFileSync(TAKEOVERS_FILE, JSON.stringify(data, null, 2), "utf-8");
		} catch {
			/* ignore */
		}
	}

	private updateSuggestionStatus(
		suggestionId: string,
		status: string,
	): boolean {
		try {
			if (!existsSync(SUGGESTIONS_FILE)) return false;
			const data = JSON.parse(readFileSync(SUGGESTIONS_FILE, "utf-8"));
			const suggestion = (data.suggestions || []).find(
				(s: LiveSuggestion) => s.suggestion_id === suggestionId,
			);
			if (!suggestion) return false;
			suggestion.status = status;
			writeFileSync(SUGGESTIONS_FILE, JSON.stringify(data, null, 2), "utf-8");
			return true;
		} catch {
			return false;
		}
	}

	private updateTakeoverStatus(proposalId: string, status: string): boolean {
		try {
			if (!existsSync(TAKEOVERS_FILE)) return false;
			const data = JSON.parse(readFileSync(TAKEOVERS_FILE, "utf-8"));
			const takeover = (data.takeovers || []).find(
				(t: TakeoverProposal) => t.proposal_id === proposalId,
			);
			if (!takeover) return false;
			takeover.status = status;
			writeFileSync(TAKEOVERS_FILE, JSON.stringify(data, null, 2), "utf-8");
			return true;
		} catch {
			return false;
		}
	}

	private getAutoBuildSourcePath(): string | null {
		if (this.autoBuildSourcePath) return this.autoBuildSourcePath;

		const validatePath = (p: string): boolean =>
			existsSync(path.join(p, "runners", "live_companion_runner.py"));

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

	private buildProcessEnvironment(): Record<string, string> {
		const processEnv: Record<string, string> = {
			...(process.env as Record<string, string>),
		};

		try {
			const settingsPath = path.join(app.getPath("userData"), "settings.json");
			if (existsSync(settingsPath)) {
				const settings: AppSettings = JSON.parse(
					readFileSync(settingsPath, "utf-8"),
				);
				if (settings.globalClaudeOAuthToken)
					processEnv.CLAUDE_OAUTH_TOKEN = settings.globalClaudeOAuthToken;
				if (settings.globalAnthropicApiKey)
					processEnv.ANTHROPIC_API_KEY = settings.globalAnthropicApiKey;
				if (settings.globalOpenAIApiKey)
					processEnv.OPENAI_API_KEY = settings.globalOpenAIApiKey;
				if (settings.globalGoogleApiKey)
					processEnv.GOOGLE_API_KEY = settings.globalGoogleApiKey;
				if (settings.globalOpenRouterApiKey)
					processEnv.OPENROUTER_API_KEY = settings.globalOpenRouterApiKey;
			}
		} catch {
			/* ignore */
		}

		return processEnv;
	}

	private detectLanguage(filePath: string): string {
		const extMap: Record<string, string> = {
			".ts": "TypeScript",
			".tsx": "TypeScript",
			".js": "JavaScript",
			".jsx": "JavaScript",
			".py": "Python",
			".rs": "Rust",
			".go": "Go",
			".java": "Java",
			".cs": "C#",
			".rb": "Ruby",
			".php": "PHP",
			".vue": "Vue",
			".svelte": "Svelte",
		};
		return extMap[path.extname(filePath).toLowerCase()] || "Unknown";
	}
}

// Singleton
export const liveCompanionService = new LiveCompanionService();
