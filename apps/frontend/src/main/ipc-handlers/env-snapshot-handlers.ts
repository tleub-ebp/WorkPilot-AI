/**
 * Environment Snapshot IPC Handlers (Feature 11).
 *
 * Spawns apps/backend/runners/env_snapshot_runner.py for each operation.
 * Snapshots are stored under <projectPath>/.workpilot/env-snapshots/.
 *
 * Channels:
 *   envSnapshot:capture → { projectPath, specId?, label? } → { snapshot }
 *   envSnapshot:list    → { projectPath } → { snapshots }
 *   envSnapshot:get     → { projectPath, snapId } → { snapshot }
 *   envSnapshot:replay  → { projectPath, snapId, format } → { payload, format }
 *   envSnapshot:export  → { projectPath, snapId, format } → { path, format }
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { app, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

type ExportFormat = "dockerfile" | "nix" | "script";

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
		"env_snapshot_runner.py",
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
							`env_snapshot_runner exited with ${code}: ${stderr || stdout}`,
						),
					);
					return;
				}
				resolve(parsed);
			} catch (err) {
				reject(
					new Error(
						`Failed to parse env_snapshot output: ${(err as Error).message} (stdout=${stdout.slice(0, 200)})`,
					),
				);
			}
		});
	});
}

export function registerEnvSnapshotHandlers(): void {
	ipcMain.handle(
		"envSnapshot:capture",
		async (
			_evt,
			{
				projectPath,
				specId,
				label,
			}: { projectPath: string; specId?: string; label?: string },
		) => {
			if (!projectPath) throw new Error("projectPath is required");
			const args = ["--command", "capture", "--project-path", projectPath];
			if (specId) args.push("--spec-id", specId);
			if (label) args.push("--label", label);
			return runRunner(args);
		},
	);

	ipcMain.handle(
		"envSnapshot:list",
		async (_evt, { projectPath }: { projectPath: string }) => {
			if (!projectPath) throw new Error("projectPath is required");
			return runRunner(["--command", "list", "--project-path", projectPath]);
		},
	);

	ipcMain.handle(
		"envSnapshot:get",
		async (
			_evt,
			{ projectPath, snapId }: { projectPath: string; snapId: string },
		) => {
			if (!projectPath || !snapId)
				throw new Error("projectPath and snapId are required");
			return runRunner([
				"--command",
				"get",
				"--project-path",
				projectPath,
				"--snap-id",
				snapId,
			]);
		},
	);

	ipcMain.handle(
		"envSnapshot:replay",
		async (
			_evt,
			{
				projectPath,
				snapId,
				format,
			}: { projectPath: string; snapId: string; format: ExportFormat },
		) => {
			if (!projectPath || !snapId)
				throw new Error("projectPath and snapId are required");
			return runRunner([
				"--command",
				"replay",
				"--project-path",
				projectPath,
				"--snap-id",
				snapId,
				"--format",
				format,
			]);
		},
	);

	ipcMain.handle(
		"envSnapshot:export",
		async (
			_evt,
			{
				projectPath,
				snapId,
				format,
			}: { projectPath: string; snapId: string; format: ExportFormat },
		) => {
			if (!projectPath || !snapId)
				throw new Error("projectPath and snapId are required");
			return runRunner([
				"--command",
				"export",
				"--project-path",
				projectPath,
				"--snap-id",
				snapId,
				"--format",
				format,
			]);
		},
	);
}
