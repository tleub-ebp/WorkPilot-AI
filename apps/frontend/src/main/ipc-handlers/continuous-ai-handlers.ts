/**
 * Continuous AI IPC Handlers
 *
 * Manages the background daemon lifecycle:
 * - Start/stop the daemon process
 * - Stream daemon events to renderer
 * - Forward approve/reject actions
 * - Persist and retrieve config
 */

import type { ChildProcess } from "node:child_process";
import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import type { BrowserWindow } from "electron";
import { ipcMain } from "electron";
import type { ContinuousAIConfig } from "../../shared/types/continuous-ai";
import { appLog } from "../app-logger";

// ─── Constants ───────────────────────────────────────────────────────────────

const DAEMON_EVENT_PREFIX = "__DAEMON_EVENT__:";

// ─── Active process tracking ─────────────────────────────────────────────────

let activeDaemonProcess: ChildProcess | null = null;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function parseDaemonEvent(line: string): Record<string, unknown> | null {
	const idx = line.indexOf(DAEMON_EVENT_PREFIX);
	if (idx === -1) return null;
	const json = line.slice(idx + DAEMON_EVENT_PREFIX.length);
	try {
		return JSON.parse(json);
	} catch {
		return null;
	}
}

function getBackendDir(): string {
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
	return fs.existsSync(resourcesPath) ? resourcesPath : devPath;
}

function getConfigDir(projectPath: string): string {
	const dir = path.join(projectPath, ".workpilot", "continuous-ai");
	if (!fs.existsSync(dir)) {
		fs.mkdirSync(dir, { recursive: true });
	}
	return dir;
}

function getConfigPath(projectPath: string): string {
	return path.join(getConfigDir(projectPath), "config.json");
}

function saveConfig(projectPath: string, config: ContinuousAIConfig): void {
	const configPath = getConfigPath(projectPath);
	fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
}

function _loadConfig(projectPath: string): ContinuousAIConfig | null {
	const configPath = getConfigPath(projectPath);
	if (!fs.existsSync(configPath)) return null;
	try {
		return JSON.parse(fs.readFileSync(configPath, "utf-8"));
	} catch {
		return null;
	}
}

function killDaemon(): void {
	if (activeDaemonProcess) {
		try {
			activeDaemonProcess.kill("SIGTERM");
			setTimeout(() => {
				if (activeDaemonProcess && !activeDaemonProcess.killed) {
					activeDaemonProcess.kill("SIGKILL");
				}
			}, 5000);
		} catch {
			// already dead
		}
		activeDaemonProcess = null;
	}
}

// ─── Registration ────────────────────────────────────────────────────────────

export function registerContinuousAIHandlers(
	getPythonPath: () => string,
	getMainWindow: () => BrowserWindow | null,
): void {
	/**
	 * Start the daemon process.
	 */
	ipcMain.handle(
		"continuousAI:start",
		async (_event, config: ContinuousAIConfig, projectPath?: string) => {
			try {
				killDaemon();

				const resolvedProject = projectPath || process.cwd();
				saveConfig(resolvedProject, config);

				appLog.info("[ContinuousAI] Starting daemon");

				const pythonPath = getPythonPath();
				const backendDir = getBackendDir();
				const runnerPath = path.join(
					backendDir,
					"runners",
					"continuous_ai_runner.py",
				);

				const proc = spawn(
					pythonPath,
					[
						runnerPath,
						"--project-dir",
						resolvedProject,
						"--config",
						JSON.stringify(config),
					],
					{
						env: {
							...process.env,
							PYTHONPATH: backendDir,
							PYTHONUNBUFFERED: "1",
							PYTHONIOENCODING: "utf-8",
							PYTHONUTF8: "1",
						},
						stdio: ["pipe", "pipe", "pipe"],
					},
				);

				activeDaemonProcess = proc;
				const win = getMainWindow();

				// Stream stdout events to renderer
				let lineBuffer = "";
				proc.stdout?.on("data", (data: Buffer) => {
					lineBuffer += data.toString();
					const lines = lineBuffer.split("\n");
					lineBuffer = lines.pop() ?? "";

					for (const line of lines) {
						const event = parseDaemonEvent(line);
						if (event && win && !win.isDestroyed()) {
							win.webContents.send("continuousAI:event", event);
						}
					}
				});

				proc.stderr?.on("data", (data: Buffer) => {
					appLog.warn(
						`[ContinuousAI] stderr: ${data.toString().slice(0, 500)}`,
					);
				});

				proc.on("close", (code) => {
					appLog.info(`[ContinuousAI] Daemon exited with code ${code}`);
					activeDaemonProcess = null;
					if (win && !win.isDestroyed()) {
						win.webContents.send("continuousAI:event", {
							type: "daemon_stopped",
							exitCode: code,
						});
					}
				});

				proc.on("error", (err) => {
					appLog.error(`[ContinuousAI] Daemon process error: ${err.message}`);
					activeDaemonProcess = null;
				});

				return { success: true, pid: proc.pid };
			} catch (err) {
				appLog.error(`[ContinuousAI] Failed to start: ${err}`);
				return {
					success: false,
					error: err instanceof Error ? err.message : "Unknown error",
				};
			}
		},
	);

	/**
	 * Stop the daemon.
	 */
	ipcMain.handle("continuousAI:stop", async () => {
		if (!activeDaemonProcess) {
			return { success: false, error: "No active daemon" };
		}
		killDaemon();
		return { success: true };
	});

	/**
	 * Get daemon status.
	 */
	ipcMain.handle(
		"continuousAI:status",
		async (_event, projectPath?: string) => {
			const resolvedProject = projectPath || process.cwd();
			const statusFile = path.join(
				resolvedProject,
				".workpilot",
				"continuous-ai",
				"status.json",
			);

			if (!fs.existsSync(statusFile)) {
				return { running: activeDaemonProcess !== null };
			}

			try {
				const data = JSON.parse(fs.readFileSync(statusFile, "utf-8"));
				data.running = activeDaemonProcess !== null;
				return data;
			} catch {
				return { running: activeDaemonProcess !== null };
			}
		},
	);

	/**
	 * Update config (persists to disk).
	 */
	ipcMain.handle(
		"continuousAI:updateConfig",
		async (_event, config: ContinuousAIConfig, projectPath?: string) => {
			const resolvedProject = projectPath || process.cwd();
			saveConfig(resolvedProject, config);
			return { success: true };
		},
	);

	/**
	 * Approve a pending action.
	 */
	ipcMain.handle(
		"continuousAI:approveAction",
		async (_event, actionId: string) => {
			// Send approval to the running daemon via stdin
			if (activeDaemonProcess?.stdin) {
				try {
					activeDaemonProcess.stdin.write(
						`${JSON.stringify({ type: "approve", actionId })}\n`,
					);
					return { success: true };
				} catch {
					return { success: false, error: "Failed to send approval" };
				}
			}
			return { success: false, error: "No active daemon" };
		},
	);

	/**
	 * Reject a pending action.
	 */
	ipcMain.handle(
		"continuousAI:rejectAction",
		async (_event, actionId: string) => {
			if (activeDaemonProcess?.stdin) {
				try {
					activeDaemonProcess.stdin.write(
						`${JSON.stringify({ type: "reject", actionId })}\n`,
					);
					return { success: true };
				} catch {
					return { success: false, error: "Failed to send rejection" };
				}
			}
			return { success: false, error: "No active daemon" };
		},
	);

	/**
	 * Check if daemon is running.
	 */
	ipcMain.handle("continuousAI:isRunning", async () => {
		return {
			running: activeDaemonProcess !== null,
			pid: activeDaemonProcess?.pid ?? null,
		};
	});
}
