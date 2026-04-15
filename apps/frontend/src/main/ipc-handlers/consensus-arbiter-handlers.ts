/**
 * Consensus Arbiter IPC Handlers
 *
 * Spawns the Python consensus arbiter runner which detects and resolves
 * inter-agent conflicts from persisted opinion payloads under
 * .workpilot/agent-opinions/.
 *
 * Channels:
 *   invoke "consensusArbiter:run"     → { projectPath }
 *   invoke "consensusArbiter:cancel"  → void
 *
 * Renderer events:
 *   consensus-arbiter-event
 *   consensus-arbiter-result
 *   consensus-arbiter-error
 */

import { type ChildProcess, spawn } from "node:child_process";
import path from "node:path";
import { app, BrowserWindow, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface RunRequest {
	projectPath: string;
}

const EVENT_PREFIX = "CONSENSUS_ARBITER_EVENT:";
const RESULT_PREFIX = "CONSENSUS_ARBITER_RESULT:";
const ERROR_PREFIX = "CONSENSUS_ARBITER_ERROR:";

function broadcast(channel: string, payload: unknown): void {
	for (const win of BrowserWindow.getAllWindows()) {
		win.webContents.send(channel, payload);
	}
}

export function registerConsensusArbiterHandlers(): void {
	let currentProcess: ChildProcess | null = null;

	const killExisting = (): void => {
		if (currentProcess) {
			currentProcess.kill("SIGTERM");
			currentProcess = null;
		}
	};

	ipcMain.handle(
		"consensusArbiter:run",
		async (_event, { projectPath }: RunRequest) => {
			killExisting();

			if (!projectPath) {
				const message = "projectPath is required";
				broadcast("consensus-arbiter-error", message);
				throw new Error(message);
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"consensus_arbiter_runner.py",
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
							broadcast("consensus-arbiter-event", payload);
						} catch (err) {
							console.error("[ConsensusArbiter] Bad event line:", err);
						}
					} else if (line.startsWith(RESULT_PREFIX)) {
						try {
							result = JSON.parse(line.slice(RESULT_PREFIX.length));
						} catch (err) {
							console.error("[ConsensusArbiter] Bad result line:", err);
						}
					} else if (line.startsWith(ERROR_PREFIX)) {
						errorMessage = line.slice(ERROR_PREFIX.length);
					}
				}
			});

			child.stderr?.on("data", (chunk: Buffer) => {
				console.error("[ConsensusArbiter] stderr:", chunk.toString());
			});

			return new Promise((resolve, reject) => {
				child.on("close", (code) => {
					currentProcess = null;
					if (code === 0 && result) {
						broadcast("consensus-arbiter-result", result);
						resolve(result);
					} else {
						const message =
							errorMessage ??
							`consensus arbiter runner exited with code ${code}`;
						broadcast("consensus-arbiter-error", message);
						reject(new Error(message));
					}
				});

				child.on("error", (err) => {
					currentProcess = null;
					const message = `Failed to start consensus arbiter runner: ${err.message}`;
					broadcast("consensus-arbiter-error", message);
					reject(new Error(message));
				});
			});
		},
	);

	ipcMain.handle("consensusArbiter:cancel", () => {
		killExisting();
		return true;
	});
}
