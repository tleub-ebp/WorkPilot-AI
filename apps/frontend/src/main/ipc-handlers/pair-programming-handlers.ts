/**
 * AI Pair Programming IPC Handlers (Feature 10)
 *
 * Manages pair programming sessions: spawns the Python runner, forwards
 * JSON-line events to the renderer, and handles user messages via a
 * temp message-queue file.
 */

import { type ChildProcess, spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { BrowserWindow } from "electron";
import { ipcMain } from "electron";
import { IPC_CHANNELS } from "../../shared/constants";
import type { IPCResult } from "../../shared/types";
import { projectStore } from "../project-store";
import { getConfiguredPythonPath } from "../python-env-manager";
import { credentialManager } from "../services/credential-manager";
import { safeSendToRenderer } from "./utils";

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PairSession {
	id: string;
	projectId: string;
	goal: string;
	devScope: string;
	aiScope: string;
	status: "planning" | "active" | "paused" | "completed" | "error";
	messages: PairMessage[];
	aiActions: AiAction[];
	createdAt: string;
	updatedAt: string;
}

interface PairMessage {
	id: string;
	role: "user" | "ai";
	content: string;
	timestamp: string;
	isQuestion?: boolean;
}

interface AiAction {
	id: string;
	actionType: string;
	description: string;
	filePath?: string;
	timestamp: string;
	status: "in_progress" | "completed" | "error";
}

interface StartSessionParams {
	projectId: string;
	goal: string;
	devScope: string;
	aiScope: string;
}

// ---------------------------------------------------------------------------
// In-memory session registry
// ---------------------------------------------------------------------------

interface ActiveSession {
	session: PairSession;
	process: ChildProcess | null;
	messagesFile: string;
	streamBuffer: string;
}

const activeSessions = new Map<string, ActiveSession>();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getBackendDir(): string {
	// In packaged app: resources/backend | In dev: apps/backend
	const devPath = path.resolve(
		__dirname,
		"..",
		"..",
		"..",
		"..",
		"apps",
		"backend",
	);
	const resourcesPath = path.resolve(process.resourcesPath || "", "backend");
	return existsSync(resourcesPath) ? resourcesPath : devPath;
}

function getRunnerPath(): string {
	return path.join(getBackendDir(), "runners", "pair_programming_runner.py");
}

function createMessagesFile(sessionId: string): string {
	const dir = path.join(os.tmpdir(), "workpilot-pair");
	mkdirSync(dir, { recursive: true });
	const filePath = path.join(dir, `${sessionId}.json`);
	writeFileSync(filePath, JSON.stringify({ pending: [] }), "utf-8");
	return filePath;
}

function appendUserMessage(messagesFile: string, content: string): void {
	try {
		const data = existsSync(messagesFile)
			? JSON.parse(readFileSync(messagesFile, "utf-8"))
			: { pending: [] };
		data.pending = data.pending || [];
		data.pending.push({ content, timestamp: new Date().toISOString() });
		writeFileSync(messagesFile, JSON.stringify(data), "utf-8");
	} catch {
		// Ignore write errors silently
	}
}

// ---------------------------------------------------------------------------
// Handler registration
// ---------------------------------------------------------------------------

export function registerPairProgrammingHandlers(
	getMainWindow: () => BrowserWindow | null,
): void {
	// ------------------------------------------------------------------
	// START SESSION
	// ------------------------------------------------------------------
	ipcMain.handle(
		IPC_CHANNELS.PAIR_PROGRAMMING_START,
		async (_, params: StartSessionParams): Promise<IPCResult<PairSession>> => {
			const { projectId, goal, devScope, aiScope } = params;

			const project = projectStore.getProject(projectId);
			if (!project) {
				return { success: false, error: "Project not found" };
			}

			// Stop any existing session for this project
			const existing = activeSessions.get(projectId);
			if (existing?.process) {
				existing.process.kill("SIGTERM");
				activeSessions.delete(projectId);
			}

			const sessionId = `pair_${Date.now()}`;
			const session: PairSession = {
				id: sessionId,
				projectId,
				goal,
				devScope,
				aiScope,
				status: "planning",
				messages: [],
				aiActions: [],
				createdAt: new Date().toISOString(),
				updatedAt: new Date().toISOString(),
			};

			const messagesFile = createMessagesFile(sessionId);

			// Spawn the Python runner
			const pythonPath = getConfiguredPythonPath() || "python3";
			const runnerPath = getRunnerPath();

			if (!existsSync(runnerPath)) {
				return { success: false, error: `Runner not found: ${runnerPath}` };
			}

			const backendDir = getBackendDir();

			// Get provider credentials (SELECTED_LLM_PROVIDER, API keys, etc.)
			// so the Python runner uses the user-selected provider instead of defaulting to Claude
			const providerEnv = credentialManager.getEnvironmentVariables();
			const nonClaudeProvider =
				providerEnv.SELECTED_LLM_PROVIDER &&
				!["claude", "anthropic"].includes(providerEnv.SELECTED_LLM_PROVIDER) &&
				providerEnv.SELECTED_LLM_PROVIDER !== "copilot";
			const claudeAuthClearVars: Record<string, string | undefined> =
				nonClaudeProvider
					? {
							CLAUDE_CODE_OAUTH_TOKEN: undefined,
							CLAUDE_CONFIG_DIR: undefined,
							ANTHROPIC_API_KEY: undefined,
							ANTHROPIC_AUTH_TOKEN: undefined,
						}
					: {};

			const proc = spawn(
				pythonPath,
				[
					runnerPath,
					"--project-dir",
					project.path,
					"--project-id",
					projectId,
					"--session-id",
					sessionId,
					"--goal",
					goal,
					"--dev-scope",
					devScope,
					"--ai-scope",
					aiScope,
					"--messages-file",
					messagesFile,
				],
				{
					cwd: backendDir,
					env: {
						...process.env,
						...claudeAuthClearVars,
						...providerEnv,
						PYTHONPATH: backendDir,
						PYTHONUNBUFFERED: "1",
						PYTHONIOENCODING: "utf-8",
						PYTHONUTF8: "1",
					} as NodeJS.ProcessEnv,
				},
			);

			const activeSession: ActiveSession = {
				session,
				process: proc,
				messagesFile,
				streamBuffer: "",
			};
			activeSessions.set(projectId, activeSession);

			// Handle stdout: JSON lines
			proc.stdout?.on("data", (data: Buffer) => {
				activeSession.streamBuffer += data.toString();
				const lines = activeSession.streamBuffer.split("\n");
				activeSession.streamBuffer = lines.pop() || "";

				for (const line of lines) {
					const trimmed = line.trim();
					if (!trimmed) continue;

					try {
						const event = JSON.parse(trimmed);
						handleRunnerEvent(event, projectId, activeSession, getMainWindow);
					} catch {
						// Non-JSON output (debug logs etc.) — forward as stream
						safeSendToRenderer(
							getMainWindow,
							IPC_CHANNELS.PAIR_PROGRAMMING_STREAM_CHUNK,
							projectId,
							{ type: "stream", content: `${trimmed}\n` },
						);
					}
				}
			});

			proc.stderr?.on("data", (data: Buffer) => {
				const msg = data.toString();
				if (msg.trim()) {
					console.error("[PairProgramming] stderr:", msg);
				}
			});

			proc.on("close", (code) => {
				const active = activeSessions.get(projectId);
				if (active) {
					active.session.status = code === 0 ? "completed" : "error";
					active.session.updatedAt = new Date().toISOString();
				}
				safeSendToRenderer(
					getMainWindow,
					IPC_CHANNELS.PAIR_PROGRAMMING_STATUS,
					projectId,
					code === 0 ? "completed" : "error",
					"",
				);
			});

			proc.on("error", (err) => {
				safeSendToRenderer(
					getMainWindow,
					IPC_CHANNELS.PAIR_PROGRAMMING_ERROR,
					projectId,
					err.message,
				);
			});

			return { success: true, data: session };
		},
	);

	// ------------------------------------------------------------------
	// STOP SESSION
	// ------------------------------------------------------------------
	ipcMain.handle(
		IPC_CHANNELS.PAIR_PROGRAMMING_STOP,
		async (_, projectId: string, _sessionId: string): Promise<IPCResult> => {
			const active = activeSessions.get(projectId);
			if (!active) {
				return { success: false, error: "No active session" };
			}
			active.process?.kill("SIGTERM");
			active.session.status = "completed";
			activeSessions.delete(projectId);
			safeSendToRenderer(
				getMainWindow,
				IPC_CHANNELS.PAIR_PROGRAMMING_STATUS,
				projectId,
				"completed",
				"Session stopped by user.",
			);
			return { success: true };
		},
	);

	// ------------------------------------------------------------------
	// SEND MESSAGE (user → AI)
	// ------------------------------------------------------------------
	ipcMain.on(
		IPC_CHANNELS.PAIR_PROGRAMMING_SEND_MESSAGE,
		(_, projectId: string, _sessionId: string, message: string) => {
			const active = activeSessions.get(projectId);
			if (!active) return;

			// Record message in session
			const msg: PairMessage = {
				id: `msg_${Date.now()}`,
				role: "user",
				content: message,
				timestamp: new Date().toISOString(),
			};
			active.session.messages.push(msg);
			active.session.updatedAt = new Date().toISOString();

			// Write to the messages file so the runner picks it up
			appendUserMessage(active.messagesFile, message);
		},
	);

	// ------------------------------------------------------------------
	// GET SESSION
	// ------------------------------------------------------------------
	ipcMain.handle(
		IPC_CHANNELS.PAIR_PROGRAMMING_GET_SESSION,
		async (_, projectId: string): Promise<IPCResult<PairSession | null>> => {
			const active = activeSessions.get(projectId);
			return { success: true, data: active?.session ?? null };
		},
	);
}

// ---------------------------------------------------------------------------
// Runner event dispatcher
// ---------------------------------------------------------------------------

function handleRunnerEvent(
	event: Record<string, unknown>,
	projectId: string,
	activeSession: ActiveSession,
	getMainWindow: () => BrowserWindow | null,
): void {
	const { type } = event;

	switch (type) {
		case "status": {
			const status = event.status as string;
			const message = event.message as string;
			if (status === "planning" || status === "active") {
				activeSession.session.status = status;
			}
			activeSession.session.updatedAt = new Date().toISOString();
			safeSendToRenderer(
				getMainWindow,
				IPC_CHANNELS.PAIR_PROGRAMMING_STATUS,
				projectId,
				status,
				message,
			);
			break;
		}

		case "stream": {
			const content = event.content as string;
			// Add AI message to session
			const lastMsg = activeSession.session.messages.at(-1);
			if (lastMsg?.role === "ai") {
				lastMsg.content += content;
			} else {
				activeSession.session.messages.push({
					id: `msg_${Date.now()}`,
					role: "ai",
					content,
					timestamp: new Date().toISOString(),
				});
			}
			safeSendToRenderer(
				getMainWindow,
				IPC_CHANNELS.PAIR_PROGRAMMING_STREAM_CHUNK,
				projectId,
				{ type: "stream", content },
			);
			break;
		}

		case "action": {
			const action: AiAction = {
				id: `action_${Date.now()}`,
				actionType: event.action_type as string,
				description: event.description as string,
				filePath: event.file_path as string | undefined,
				timestamp: (event.timestamp as string) || new Date().toISOString(),
				status: "completed",
			};
			activeSession.session.aiActions.push(action);
			activeSession.session.updatedAt = new Date().toISOString();
			safeSendToRenderer(
				getMainWindow,
				IPC_CHANNELS.PAIR_PROGRAMMING_AI_ACTION,
				projectId,
				action,
			);
			break;
		}

		case "question": {
			const content = event.content as string;
			const qMsg: PairMessage = {
				id: `msg_${Date.now()}`,
				role: "ai",
				content,
				timestamp: new Date().toISOString(),
				isQuestion: true,
			};
			activeSession.session.messages.push(qMsg);
			safeSendToRenderer(
				getMainWindow,
				IPC_CHANNELS.PAIR_PROGRAMMING_STREAM_CHUNK,
				projectId,
				{ type: "question", content },
			);
			break;
		}

		case "conflict": {
			const filePath = event.file_path as string;
			const message = event.message as string;
			safeSendToRenderer(
				getMainWindow,
				IPC_CHANNELS.PAIR_PROGRAMMING_CONFLICT,
				projectId,
				filePath,
				message,
			);
			break;
		}

		case "done": {
			const summary = event.summary as string;
			activeSession.session.status = "completed";
			activeSession.session.updatedAt = new Date().toISOString();
			safeSendToRenderer(
				getMainWindow,
				IPC_CHANNELS.PAIR_PROGRAMMING_STREAM_CHUNK,
				projectId,
				{ type: "done", summary },
			);
			safeSendToRenderer(
				getMainWindow,
				IPC_CHANNELS.PAIR_PROGRAMMING_COMPLETE,
				projectId,
				summary,
			);
			break;
		}

		case "error": {
			const errMsg = event.message as string;
			activeSession.session.status = "error";
			activeSession.session.updatedAt = new Date().toISOString();
			safeSendToRenderer(
				getMainWindow,
				IPC_CHANNELS.PAIR_PROGRAMMING_ERROR,
				projectId,
				errMsg,
			);
			break;
		}

		default:
			break;
	}
}
