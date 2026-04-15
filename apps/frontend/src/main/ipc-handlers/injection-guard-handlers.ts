/**
 * Injection Guard IPC Handlers
 *
 * Spawns the Python injection guard runner which scans persisted prompt
 * payloads under .workpilot/prompts/ for prompt injection attempts.
 *
 * Channels:
 *   invoke "injectionGuard:run"     → { projectPath }
 *   invoke "injectionGuard:cancel"  → void
 *
 * Renderer events:
 *   injection-guard-event
 *   injection-guard-result
 *   injection-guard-error
 */

import { type ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { app, BrowserWindow, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface RunRequest {
	projectPath: string;
}

const EVENT_PREFIX = "INJECTION_GUARD_EVENT:";
const RESULT_PREFIX = "INJECTION_GUARD_RESULT:";
const ERROR_PREFIX = "INJECTION_GUARD_ERROR:";

function broadcast(channel: string, payload: unknown): void {
	for (const win of BrowserWindow.getAllWindows()) {
		win.webContents.send(channel, payload);
	}
}

export function registerInjectionGuardHandlers(): void {
	let currentProcess: ChildProcess | null = null;

	const killExisting = (): void => {
		if (currentProcess) {
			currentProcess.kill("SIGTERM");
			currentProcess = null;
		}
	};

	ipcMain.handle(
		"injectionGuard:run",
		async (_event, { projectPath }: RunRequest) => {
			killExisting();

			if (!projectPath) {
				const message = "projectPath is required";
				broadcast("injection-guard-error", message);
				throw new Error(message);
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"injection_guard_runner.py",
			);

			const pythonExe = pythonEnvManager.getPythonPath();
			if (!pythonExe) {
				throw new Error("Python environment not ready");
			}

			const child = spawn(
				pythonExe,
				[runnerPath, "--project-path", projectPath],
				{
					cwd: backendPath,
					env: { ...process.env, PYTHONPATH: backendPath },
				} as Parameters<typeof spawn>[2],
			);
			currentProcess = child;

			let buffer = "";
			let result: unknown = null;
			let errorMessage: string | null = null;

			child.stdout?.on("data", (chunk: Buffer) => {
				buffer += chunk.toString();
				let newlineIdx = buffer.indexOf("\n");
				while (newlineIdx >= 0) {
					const line = buffer.slice(0, newlineIdx).trim();
					buffer = buffer.slice(newlineIdx + 1);
					newlineIdx = buffer.indexOf("\n");
					if (!line) continue;

					if (line.startsWith(EVENT_PREFIX)) {
						try {
							const payload = JSON.parse(line.slice(EVENT_PREFIX.length));
							broadcast("injection-guard-event", payload);
						} catch (err) {
							console.error("[InjectionGuard] Bad event line:", err);
						}
					} else if (line.startsWith(RESULT_PREFIX)) {
						try {
							result = JSON.parse(line.slice(RESULT_PREFIX.length));
						} catch (err) {
							console.error("[InjectionGuard] Bad result line:", err);
						}
					} else if (line.startsWith(ERROR_PREFIX)) {
						errorMessage = line.slice(ERROR_PREFIX.length);
					}
				}
			});

			child.stderr?.on("data", (chunk: Buffer) => {
				console.error("[InjectionGuard] stderr:", chunk.toString());
			});

			return new Promise((resolve, reject) => {
				child.on("close", (code) => {
					currentProcess = null;
					if (code === 0 && result) {
						broadcast("injection-guard-result", result);
						resolve(result);
					} else {
						const message =
							errorMessage ??
							`injection guard runner exited with code ${code}`;
						broadcast("injection-guard-error", message);
						reject(new Error(message));
					}
				});

				child.on("error", (err) => {
					currentProcess = null;
					const message = `Failed to start injection guard runner: ${err.message}`;
					broadcast("injection-guard-error", message);
					reject(new Error(message));
				});
			});
		},
	);

	ipcMain.handle("injectionGuard:cancel", () => {
		killExisting();
		return true;
	});
}
