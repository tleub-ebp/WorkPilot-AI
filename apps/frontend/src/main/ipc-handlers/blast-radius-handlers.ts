/**
 * Blast Radius IPC Handlers
 *
 * Channel: blastRadius:analyze
 *   → { projectRoot, targets: string[] } → BlastRadiusReport
 *
 * Provider-agnostic: calls the deterministic Python analyser (no LLM).
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { app, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

function runAnalysis(
	projectRoot: string,
	targets: string[],
): Promise<unknown> {
	const backendPath = app.isPackaged
		? path.resolve(process.resourcesPath, "backend")
		: path.resolve(app.getAppPath(), "..", "backend");
	const runnerPath = path.resolve(
		backendPath,
		"runners",
		"blast_radius_runner.py",
	);
	const pythonExe = pythonEnvManager.getPythonPath();
	if (!pythonExe) return Promise.reject(new Error("Python env not ready"));

	const args = [
		runnerPath,
		"--project-root",
		projectRoot,
		"--targets",
		targets.join(","),
	];

	return new Promise((resolve, reject) => {
		const child = spawn(pythonExe, args, {
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
			const last = stdout.trim().split("\n").filter(Boolean).pop() ?? "";
			try {
				const parsed = JSON.parse(last) as Record<string, unknown>;
				if (parsed.error) {
					reject(new Error(String(parsed.error)));
					return;
				}
				if (code !== 0) {
					reject(new Error(`runner exit ${code}: ${stderr}`));
					return;
				}
				resolve(parsed);
			} catch (err) {
				reject(
					new Error(
						`Failed to parse blast-radius runner output: ${(err as Error).message}`,
					),
				);
			}
		});
	});
}

export function registerBlastRadiusHandlers(): void {
	ipcMain.handle(
		"blastRadius:analyze",
		async (
			_e,
			{
				projectRoot,
				targets,
			}: { projectRoot: string; targets: string[] },
		) => runAnalysis(projectRoot, targets),
	);
}
