/**
 * Offline Mode IPC Handlers (Feature 12).
 *
 * Spawns apps/backend/runners/offline_mode_runner.py.
 *
 * Channels:
 *   offlineMode:status       → { projectPath } → status payload
 *   offlineMode:listModels   → { projectPath } → status payload (models focus)
 *   offlineMode:scanModels   → { projectPath, force? } → provider catalog (TTL-cached)
 *   offlineMode:getPolicy    → { projectPath } → { policy }
 *   offlineMode:setPolicy    → { projectPath, policy } → { policy }
 *   offlineMode:report       → { projectPath } → report payload
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { app, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

function resolveBackendPath(): string {
	return app.isPackaged
		? path.resolve(process.resourcesPath, "backend")
		: path.resolve(app.getAppPath(), "..", "backend");
}

function runRunner(args: string[]): Promise<unknown> {
	const pythonExe = pythonEnvManager.getPythonPath();
	if (!pythonExe) throw new Error("Python environment not ready");

	const backendPath = resolveBackendPath();
	const runnerPath = path.resolve(
		backendPath,
		"runners",
		"offline_mode_runner.py",
	);

	return new Promise((resolve, reject) => {
		const child = spawn(pythonExe, [runnerPath, ...args], {
			cwd: backendPath,
			env: { ...process.env, PYTHONPATH: backendPath },
		} as Parameters<typeof spawn>[2]);

		let stdout = "";
		let stderr = "";
		child.stdout?.on("data", (c: Buffer) => {
			stdout += c.toString();
		});
		child.stderr?.on("data", (c: Buffer) => {
			stderr += c.toString();
		});
		child.on("error", reject);
		child.on("close", (code) => {
			const lines = stdout.trim().split("\n").filter(Boolean);
			const lastLine = lines[lines.length - 1] ?? "";
			try {
				const parsed = JSON.parse(lastLine);
				if (parsed.error) {
					reject(new Error(parsed.error));
					return;
				}
				if (code !== 0) {
					reject(
						new Error(
							`offline_mode_runner exited with ${code}: ${stderr || stdout}`,
						),
					);
					return;
				}
				resolve(parsed);
			} catch (err) {
				reject(
					new Error(
						`Failed to parse offline_mode output: ${(err as Error).message} (stdout=${stdout.slice(0, 200)})`,
					),
				);
			}
		});
	});
}

export function registerOfflineModeHandlers(): void {
	ipcMain.handle(
		"offlineMode:status",
		async (_evt, { projectPath }: { projectPath: string }) => {
			if (!projectPath) throw new Error("projectPath is required");
			return runRunner(["--command", "status", "--project-path", projectPath]);
		},
	);

	ipcMain.handle(
		"offlineMode:listModels",
		async (_evt, { projectPath }: { projectPath: string }) => {
			if (!projectPath) throw new Error("projectPath is required");
			return runRunner([
				"--command",
				"list-models",
				"--project-path",
				projectPath,
			]);
		},
	);

	ipcMain.handle(
		"offlineMode:scanModels",
		async (
			_evt,
			{
				projectPath,
				force,
			}: { projectPath: string; force?: boolean },
		) => {
			if (!projectPath) throw new Error("projectPath is required");
			const args = ["--command", "scan-models", "--project-path", projectPath];
			if (force) args.push("--force");
			return runRunner(args);
		},
	);

	ipcMain.handle(
		"offlineMode:getPolicy",
		async (_evt, { projectPath }: { projectPath: string }) => {
			if (!projectPath) throw new Error("projectPath is required");
			return runRunner([
				"--command",
				"get-policy",
				"--project-path",
				projectPath,
			]);
		},
	);

	ipcMain.handle(
		"offlineMode:setPolicy",
		async (
			_evt,
			{
				projectPath,
				policy,
			}: { projectPath: string; policy: Record<string, unknown> },
		) => {
			if (!projectPath) throw new Error("projectPath is required");
			return runRunner([
				"--command",
				"set-policy",
				"--project-path",
				projectPath,
				"--policy-json",
				JSON.stringify(policy),
			]);
		},
	);

	ipcMain.handle(
		"offlineMode:report",
		async (_evt, { projectPath }: { projectPath: string }) => {
			if (!projectPath) throw new Error("projectPath is required");
			return runRunner(["--command", "report", "--project-path", projectPath]);
		},
	);
}
