/**
 * Onboarding Agent IPC Handlers
 *
 * Spawns the Python onboarding agent runner which analyses a project and
 * returns an onboarding guide.
 *
 * Channels:
 *   invoke "onboardingAgent:run"     → { projectPath }
 *   invoke "onboardingAgent:cancel"  → void
 *
 * Renderer events:
 *   onboarding-event
 *   onboarding-result
 *   onboarding-error
 */

import { type ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { app, BrowserWindow, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface RunRequest {
	projectPath: string;
}

const EVENT_PREFIX = "ONBOARDING_EVENT:";
const RESULT_PREFIX = "ONBOARDING_RESULT:";
const ERROR_PREFIX = "ONBOARDING_ERROR:";

function broadcast(channel: string, payload: unknown): void {
	for (const win of BrowserWindow.getAllWindows()) {
		win.webContents.send(channel, payload);
	}
}

export function registerOnboardingAgentHandlers(): void {
	let currentProcess: ChildProcess | null = null;

	const killExisting = (): void => {
		if (currentProcess) {
			currentProcess.kill("SIGTERM");
			currentProcess = null;
		}
	};

	ipcMain.handle(
		"onboardingAgent:run",
		async (_event, { projectPath }: RunRequest) => {
			killExisting();

			if (!projectPath) {
				const message = "projectPath is required";
				broadcast("onboarding-error", message);
				throw new Error(message);
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"onboarding_agent_runner.py",
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
							broadcast("onboarding-event", payload);
						} catch (err) {
							console.error("[Onboarding] Bad event line:", err);
						}
					} else if (line.startsWith(RESULT_PREFIX)) {
						try {
							result = JSON.parse(line.slice(RESULT_PREFIX.length));
						} catch (err) {
							console.error("[Onboarding] Bad result line:", err);
						}
					} else if (line.startsWith(ERROR_PREFIX)) {
						errorMessage = line.slice(ERROR_PREFIX.length);
					}
				}
			});

			child.stderr?.on("data", (chunk: Buffer) => {
				console.error("[Onboarding] stderr:", chunk.toString());
			});

			return new Promise((resolve, reject) => {
				child.on("close", (code) => {
					currentProcess = null;
					if (code === 0 && result) {
						broadcast("onboarding-result", result);
						resolve(result);
					} else {
						const message =
							errorMessage ?? `onboarding runner exited with code ${code}`;
						broadcast("onboarding-error", message);
						reject(new Error(message));
					}
				});

				child.on("error", (err) => {
					currentProcess = null;
					const message = `Failed to start onboarding runner: ${err.message}`;
					broadcast("onboarding-error", message);
					reject(new Error(message));
				});
			});
		},
	);

	ipcMain.handle("onboardingAgent:cancel", () => {
		killExisting();
		return true;
	});
}
