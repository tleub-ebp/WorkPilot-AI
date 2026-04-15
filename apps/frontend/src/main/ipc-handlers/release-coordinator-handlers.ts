/**
 * Release Coordinator IPC Handlers
 *
 * Spawns the Python release coordinator runner.
 *
 * Channels:
 *   invoke "releaseCoordinator:run"     → { projectPath, maxCommits? }
 *   invoke "releaseCoordinator:cancel"  → void
 *
 * Renderer events:
 *   release-coordinator-event
 *   release-coordinator-result
 *   release-coordinator-error
 */

import { type ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { app, BrowserWindow, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface RunRequest {
	projectPath: string;
	maxCommits?: number;
}

const EVENT_PREFIX = "RELEASE_COORDINATOR_EVENT:";
const RESULT_PREFIX = "RELEASE_COORDINATOR_RESULT:";
const ERROR_PREFIX = "RELEASE_COORDINATOR_ERROR:";

function broadcast(channel: string, payload: unknown): void {
	for (const win of BrowserWindow.getAllWindows()) {
		win.webContents.send(channel, payload);
	}
}

export function registerReleaseCoordinatorHandlers(): void {
	let currentProcess: ChildProcess | null = null;

	const killExisting = (): void => {
		if (currentProcess) {
			currentProcess.kill("SIGTERM");
			currentProcess = null;
		}
	};

	ipcMain.handle(
		"releaseCoordinator:run",
		async (_event, { projectPath, maxCommits = 100 }: RunRequest) => {
			killExisting();

			if (!projectPath) {
				const message = "projectPath is required";
				broadcast("release-coordinator-error", message);
				throw new Error(message);
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"release_coordinator_runner.py",
			);

			const pythonExe = pythonEnvManager.getPythonPath();
			if (!pythonExe) {
				throw new Error("Python environment not ready");
			}

			const child = spawn(
				pythonExe,
				[
					runnerPath,
					"--project-path",
					projectPath,
					"--max-commits",
					String(maxCommits),
				],
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
							broadcast("release-coordinator-event", payload);
						} catch (err) {
							console.error("[ReleaseCoordinator] Bad event line:", err);
						}
					} else if (line.startsWith(RESULT_PREFIX)) {
						try {
							result = JSON.parse(line.slice(RESULT_PREFIX.length));
						} catch (err) {
							console.error("[ReleaseCoordinator] Bad result line:", err);
						}
					} else if (line.startsWith(ERROR_PREFIX)) {
						errorMessage = line.slice(ERROR_PREFIX.length);
					}
				}
			});

			child.stderr?.on("data", (chunk: Buffer) => {
				console.error("[ReleaseCoordinator] stderr:", chunk.toString());
			});

			return new Promise((resolve, reject) => {
				child.on("close", (code) => {
					currentProcess = null;
					if (code === 0 && result) {
						broadcast("release-coordinator-result", result);
						resolve(result);
					} else {
						const message =
							errorMessage ??
							`release coordinator runner exited with code ${code}`;
						broadcast("release-coordinator-error", message);
						reject(new Error(message));
					}
				});

				child.on("error", (err) => {
					currentProcess = null;
					const message = `Failed to start release coordinator runner: ${err.message}`;
					broadcast("release-coordinator-error", message);
					reject(new Error(message));
				});
			});
		},
	);

	ipcMain.handle("releaseCoordinator:cancel", () => {
		killExisting();
		return true;
	});
}
