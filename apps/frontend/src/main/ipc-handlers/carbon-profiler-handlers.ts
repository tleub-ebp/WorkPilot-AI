/**
 * Carbon Profiler IPC Handlers
 *
 * Spawns the Python carbon profiler runner.
 *
 * Channels:
 *   invoke "carbonProfiler:run"     → { projectPath, region? }
 *   invoke "carbonProfiler:cancel"  → void
 *
 * Renderer events:
 *   carbon-profiler-event     (progress / start / complete metadata)
 *   carbon-profiler-result    (full CarbonReport JSON)
 *   carbon-profiler-error     (string)
 */

import { type ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { app, BrowserWindow, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface RunRequest {
	projectPath: string;
	region?: string;
}

const EVENT_PREFIX = "CARBON_EVENT:";
const RESULT_PREFIX = "CARBON_RESULT:";
const ERROR_PREFIX = "CARBON_ERROR:";

function broadcast(channel: string, payload: unknown): void {
	for (const win of BrowserWindow.getAllWindows()) {
		win.webContents.send(channel, payload);
	}
}

export function registerCarbonProfilerHandlers(): void {
	let currentProcess: ChildProcess | null = null;

	const killExisting = (): void => {
		if (currentProcess) {
			currentProcess.kill("SIGTERM");
			currentProcess = null;
		}
	};

	ipcMain.handle(
		"carbonProfiler:run",
		async (_event, { projectPath, region = "global_avg" }: RunRequest) => {
			killExisting();

			if (!projectPath) {
				const message = "projectPath is required";
				broadcast("carbon-profiler-error", message);
				throw new Error(message);
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"carbon_profiler_runner.py",
			);

			const pythonExe = pythonEnvManager.getPythonPath();
			if (!pythonExe) {
				throw new Error("Python environment not ready");
			}

			const child = spawn(
				pythonExe,
				[runnerPath, "--project-path", projectPath, "--region", region],
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
							broadcast("carbon-profiler-event", payload);
						} catch (err) {
							console.error("[CarbonProfiler] Bad event line:", err);
						}
					} else if (line.startsWith(RESULT_PREFIX)) {
						try {
							result = JSON.parse(line.slice(RESULT_PREFIX.length));
						} catch (err) {
							console.error("[CarbonProfiler] Bad result line:", err);
						}
					} else if (line.startsWith(ERROR_PREFIX)) {
						errorMessage = line.slice(ERROR_PREFIX.length);
					}
				}
			});

			child.stderr?.on("data", (chunk: Buffer) => {
				console.error("[CarbonProfiler] stderr:", chunk.toString());
			});

			return new Promise((resolve, reject) => {
				child.on("close", (code) => {
					currentProcess = null;
					if (code === 0 && result) {
						broadcast("carbon-profiler-result", result);
						resolve(result);
					} else {
						const message =
							errorMessage ?? `carbon profiler runner exited with code ${code}`;
						broadcast("carbon-profiler-error", message);
						reject(new Error(message));
					}
				});

				child.on("error", (err) => {
					currentProcess = null;
					const message = `Failed to start carbon profiler runner: ${err.message}`;
					broadcast("carbon-profiler-error", message);
					reject(new Error(message));
				});
			});
		},
	);

	ipcMain.handle("carbonProfiler:cancel", () => {
		killExisting();
		return true;
	});
}
