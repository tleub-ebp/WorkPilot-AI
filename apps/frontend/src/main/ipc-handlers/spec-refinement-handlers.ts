/**
 * Spec Refinement IPC Handlers
 *
 * Spawns the Python spec refinement runner which discovers persisted
 * refinement histories under .workpilot/refinement-histories/.
 *
 * Channels:
 *   invoke "specRefinement:run"     → { projectPath }
 *   invoke "specRefinement:cancel"  → void
 *
 * Renderer events:
 *   spec-refinement-event
 *   spec-refinement-result
 *   spec-refinement-error
 */

import { type ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { app, BrowserWindow, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface RunRequest {
	projectPath: string;
}

const EVENT_PREFIX = "SPEC_REFINEMENT_EVENT:";
const RESULT_PREFIX = "SPEC_REFINEMENT_RESULT:";
const ERROR_PREFIX = "SPEC_REFINEMENT_ERROR:";

function broadcast(channel: string, payload: unknown): void {
	for (const win of BrowserWindow.getAllWindows()) {
		win.webContents.send(channel, payload);
	}
}

export function registerSpecRefinementHandlers(): void {
	let currentProcess: ChildProcess | null = null;

	const killExisting = (): void => {
		if (currentProcess) {
			currentProcess.kill("SIGTERM");
			currentProcess = null;
		}
	};

	ipcMain.handle(
		"specRefinement:run",
		async (_event, { projectPath }: RunRequest) => {
			killExisting();

			if (!projectPath) {
				const message = "projectPath is required";
				broadcast("spec-refinement-error", message);
				throw new Error(message);
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"spec_refinement_runner.py",
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
							broadcast("spec-refinement-event", payload);
						} catch (err) {
							console.error("[SpecRefinement] Bad event line:", err);
						}
					} else if (line.startsWith(RESULT_PREFIX)) {
						try {
							result = JSON.parse(line.slice(RESULT_PREFIX.length));
						} catch (err) {
							console.error("[SpecRefinement] Bad result line:", err);
						}
					} else if (line.startsWith(ERROR_PREFIX)) {
						errorMessage = line.slice(ERROR_PREFIX.length);
					}
				}
			});

			child.stderr?.on("data", (chunk: Buffer) => {
				console.error("[SpecRefinement] stderr:", chunk.toString());
			});

			return new Promise((resolve, reject) => {
				child.on("close", (code) => {
					currentProcess = null;
					if (code === 0 && result) {
						broadcast("spec-refinement-result", result);
						resolve(result);
					} else {
						const message =
							errorMessage ?? `spec refinement runner exited with code ${code}`;
						broadcast("spec-refinement-error", message);
						reject(new Error(message));
					}
				});

				child.on("error", (err) => {
					currentProcess = null;
					const message = `Failed to start spec refinement runner: ${err.message}`;
					broadcast("spec-refinement-error", message);
					reject(new Error(message));
				});
			});
		},
	);

	ipcMain.handle("specRefinement:cancel", () => {
		killExisting();
		return true;
	});
}
