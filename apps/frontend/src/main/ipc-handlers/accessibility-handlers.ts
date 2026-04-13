/**
 * Accessibility Agent IPC Handlers
 *
 * Spawns the Python accessibility runner and forwards events,
 * the structured report, and any errors back to the renderer.
 *
 * Channels:
 *   invoke "accessibility:run"     → { projectPath, targetLevel? }
 *   invoke "accessibility:cancel"  → void
 *
 * Renderer events:
 *   accessibility-event     (progress / start / complete metadata)
 *   accessibility-result    (full A11yReport JSON)
 *   accessibility-error     (string)
 */

import { type ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { app, BrowserWindow, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface RunRequest {
	projectPath: string;
	targetLevel?: "A" | "AA" | "AAA";
}

const EVENT_PREFIX = "A11Y_EVENT:";
const RESULT_PREFIX = "A11Y_RESULT:";
const ERROR_PREFIX = "A11Y_ERROR:";

function broadcast(channel: string, payload: unknown): void {
	for (const win of BrowserWindow.getAllWindows()) {
		win.webContents.send(channel, payload);
	}
}

export function registerAccessibilityHandlers(): void {
	let currentProcess: ChildProcess | null = null;

	const killExisting = (): void => {
		if (currentProcess) {
			currentProcess.kill("SIGTERM");
			currentProcess = null;
		}
	};

	ipcMain.handle(
		"accessibility:run",
		async (_event, { projectPath, targetLevel = "AA" }: RunRequest) => {
			killExisting();

			if (!projectPath) {
				const message = "projectPath is required";
				broadcast("accessibility-error", message);
				throw new Error(message);
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"accessibility_runner.py",
			);

			// Use PythonEnvManager to get the configured Python path
			const pythonExe = pythonEnvManager.getPythonPath();

			if (!pythonExe) {
				throw new Error("Python environment not ready");
			}

			const child = spawn(
				pythonExe,
				[runnerPath, "--project-path", projectPath, "--target-level", targetLevel],
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
							broadcast("accessibility-event", payload);
						} catch (err) {
							console.error("[Accessibility] Bad event line:", err);
						}
					} else if (line.startsWith(RESULT_PREFIX)) {
						try {
							result = JSON.parse(line.slice(RESULT_PREFIX.length));
						} catch (err) {
							console.error("[Accessibility] Bad result line:", err);
						}
					} else if (line.startsWith(ERROR_PREFIX)) {
						errorMessage = line.slice(ERROR_PREFIX.length);
					}
				}
			});

			child.stderr?.on("data", (chunk: Buffer) => {
				console.error("[Accessibility] stderr:", chunk.toString());
			});

			return new Promise((resolve, reject) => {
				child.on("close", (code) => {
					currentProcess = null;
					if (code === 0 && result) {
						broadcast("accessibility-result", result);
						resolve(result);
					} else {
						const message =
							errorMessage ?? `accessibility runner exited with code ${code}`;
						broadcast("accessibility-error", message);
						reject(new Error(message));
					}
				});

				child.on("error", (err) => {
					currentProcess = null;
					const message = `Failed to start accessibility runner: ${err.message}`;
					broadcast("accessibility-error", message);
					reject(new Error(message));
				});
			});
		},
	);

	ipcMain.handle("accessibility:cancel", () => {
		killExisting();
		return true;
	});
}
