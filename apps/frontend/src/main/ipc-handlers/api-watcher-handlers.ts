/**
 * API Watcher IPC Handlers
 *
 * Spawns the Python API watcher runner to detect breaking contract changes.
 *
 * Channels:
 *   invoke "apiWatcher:run"          → { projectPath, saveBaseline? }
 *   invoke "apiWatcher:cancel"       → void
 *
 * Renderer events:
 *   api-watcher-event
 *   api-watcher-result
 *   api-watcher-error
 */

import { type ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { app, BrowserWindow, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface RunRequest {
	projectPath: string;
	saveBaseline?: boolean;
}

const EVENT_PREFIX = "API_WATCHER_EVENT:";
const RESULT_PREFIX = "API_WATCHER_RESULT:";
const ERROR_PREFIX = "API_WATCHER_ERROR:";

function broadcast(channel: string, payload: unknown): void {
	for (const win of BrowserWindow.getAllWindows()) {
		win.webContents.send(channel, payload);
	}
}

export function registerApiWatcherHandlers(): void {
	let currentProcess: ChildProcess | null = null;

	const killExisting = (): void => {
		if (currentProcess) {
			currentProcess.kill("SIGTERM");
			currentProcess = null;
		}
	};

	ipcMain.handle(
		"apiWatcher:run",
		async (_event, { projectPath, saveBaseline = false }: RunRequest) => {
			killExisting();

			if (!projectPath) {
				const message = "projectPath is required";
				broadcast("api-watcher-error", message);
				throw new Error(message);
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"api_watcher_runner.py",
			);

			const pythonExe = pythonEnvManager.getPythonPath();
			if (!pythonExe) {
				throw new Error("Python environment not ready");
			}

			const args = [runnerPath, "--project-path", projectPath];
			if (saveBaseline) args.push("--save-baseline");

			const child = spawn(pythonExe, args, {
				cwd: backendPath,
				env: { ...process.env, PYTHONPATH: backendPath },
			} as Parameters<typeof spawn>[2]);
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
							broadcast("api-watcher-event", payload);
						} catch (err) {
							console.error("[APIWatcher] Bad event line:", err);
						}
					} else if (line.startsWith(RESULT_PREFIX)) {
						try {
							result = JSON.parse(line.slice(RESULT_PREFIX.length));
						} catch (err) {
							console.error("[APIWatcher] Bad result line:", err);
						}
					} else if (line.startsWith(ERROR_PREFIX)) {
						errorMessage = line.slice(ERROR_PREFIX.length);
					}
				}
			});

			child.stderr?.on("data", (chunk: Buffer) => {
				console.error("[APIWatcher] stderr:", chunk.toString());
			});

			return new Promise((resolve, reject) => {
				child.on("close", (code) => {
					currentProcess = null;
					if (code === 0 && result) {
						broadcast("api-watcher-result", result);
						resolve(result);
					} else {
						const message =
							errorMessage ?? `api watcher runner exited with code ${code}`;
						broadcast("api-watcher-error", message);
						reject(new Error(message));
					}
				});

				child.on("error", (err) => {
					currentProcess = null;
					const message = `Failed to start api watcher runner: ${err.message}`;
					broadcast("api-watcher-error", message);
					reject(new Error(message));
				});
			});
		},
	);

	ipcMain.handle("apiWatcher:cancel", () => {
		killExisting();
		return true;
	});
}
