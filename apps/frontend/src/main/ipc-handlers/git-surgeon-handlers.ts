/**
 * Git Surgeon IPC Handlers
 *
 * Spawns the Python git surgeon runner to analyse git history.
 *
 * Channels:
 *   invoke "gitSurgeon:run"     → { projectPath, maxCommits? }
 *   invoke "gitSurgeon:cancel"  → void
 *
 * Renderer events:
 *   git-surgeon-event
 *   git-surgeon-result
 *   git-surgeon-error
 */

import { type ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { app, BrowserWindow, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface RunRequest {
	projectPath: string;
	maxCommits?: number;
}

const EVENT_PREFIX = "GIT_SURGEON_EVENT:";
const RESULT_PREFIX = "GIT_SURGEON_RESULT:";
const ERROR_PREFIX = "GIT_SURGEON_ERROR:";

function broadcast(channel: string, payload: unknown): void {
	for (const win of BrowserWindow.getAllWindows()) {
		win.webContents.send(channel, payload);
	}
}

export function registerGitSurgeonHandlers(): void {
	let currentProcess: ChildProcess | null = null;

	const killExisting = (): void => {
		if (currentProcess) {
			currentProcess.kill("SIGTERM");
			currentProcess = null;
		}
	};

	ipcMain.handle(
		"gitSurgeon:run",
		async (_event, { projectPath, maxCommits = 500 }: RunRequest) => {
			killExisting();

			if (!projectPath) {
				const message = "projectPath is required";
				broadcast("git-surgeon-error", message);
				throw new Error(message);
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"git_surgeon_runner.py",
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
							broadcast("git-surgeon-event", payload);
						} catch (err) {
							console.error("[GitSurgeon] Bad event line:", err);
						}
					} else if (line.startsWith(RESULT_PREFIX)) {
						try {
							result = JSON.parse(line.slice(RESULT_PREFIX.length));
						} catch (err) {
							console.error("[GitSurgeon] Bad result line:", err);
						}
					} else if (line.startsWith(ERROR_PREFIX)) {
						errorMessage = line.slice(ERROR_PREFIX.length);
					}
				}
			});

			child.stderr?.on("data", (chunk: Buffer) => {
				console.error("[GitSurgeon] stderr:", chunk.toString());
			});

			return new Promise((resolve, reject) => {
				child.on("close", (code) => {
					currentProcess = null;
					if (code === 0 && result) {
						broadcast("git-surgeon-result", result);
						resolve(result);
					} else {
						const message =
							errorMessage ?? `git surgeon runner exited with code ${code}`;
						broadcast("git-surgeon-error", message);
						reject(new Error(message));
					}
				});

				child.on("error", (err) => {
					currentProcess = null;
					const message = `Failed to start git surgeon runner: ${err.message}`;
					broadcast("git-surgeon-error", message);
					reject(new Error(message));
				});
			});
		},
	);

	ipcMain.handle("gitSurgeon:cancel", () => {
		killExisting();
		return true;
	});
}
