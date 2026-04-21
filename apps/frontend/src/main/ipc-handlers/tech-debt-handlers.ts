/**
 * Tech Debt IPC Handlers.
 *
 * Spawns apps/backend/runners/tech_debt_runner.py to scan a project and
 * score each debt item by ROI = cost / effort.
 *
 * Channels:
 *   invoke "techDebt:scan"       → { projectPath } → { result }
 *   invoke "techDebt:listItems"  → { projectPath, minScore? } → { result }
 *   invoke "techDebt:getTrend"   → { projectPath } → { result }
 *   invoke "techDebt:generateSpec" → { projectPath, itemId, llmHint? } → { result }
 */

import path from "node:path";
import { spawn } from "node:child_process";
import { app, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface ScanRequest {
	projectPath: string;
}
interface ListRequest {
	projectPath: string;
	minScore?: number;
}
interface SpecRequest {
	projectPath: string;
	itemId: string;
	llmHint?: string;
}

function resolveBackendPaths(): { backendPath: string; runnerPath: string } {
	const backendPath = app.isPackaged
		? path.resolve(process.resourcesPath, "backend")
		: path.resolve(app.getAppPath(), "..", "backend");
	const runnerPath = path.resolve(
		backendPath,
		"runners",
		"tech_debt_runner.py",
	);
	return { backendPath, runnerPath };
}

function runRunner(args: string[]): Promise<unknown> {
	const { backendPath, runnerPath } = resolveBackendPaths();
	const pythonExe = pythonEnvManager.getPythonPath();
	if (!pythonExe) return Promise.reject(new Error("Python environment not ready"));

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
		child.on("error", (err) => reject(err));
		child.on("close", (code) => {
			const lines = stdout.trim().split("\n").filter(Boolean);
			const last = lines[lines.length - 1] ?? "";
			try {
				const parsed = JSON.parse(last);
				if (parsed.error) return reject(new Error(parsed.error));
				if (code !== 0) {
					return reject(
						new Error(`tech_debt_runner exited with ${code}: ${stderr}`),
					);
				}
				resolve(parsed.result);
			} catch (err) {
				reject(
					new Error(
						`Failed to parse runner output: ${(err as Error).message}`,
					),
				);
			}
		});
	});
}

export function registerTechDebtHandlers(): void {
	ipcMain.handle("techDebt:scan", async (_e, req: ScanRequest) => {
		if (!req.projectPath) throw new Error("projectPath is required");
		const result = await runRunner([
			"--project-path",
			req.projectPath,
			"--command",
			"scan",
		]);
		return { result };
	});

	ipcMain.handle("techDebt:listItems", async (_e, req: ListRequest) => {
		if (!req.projectPath) throw new Error("projectPath is required");
		const args = [
			"--project-path",
			req.projectPath,
			"--command",
			"list",
		];
		if (req.minScore !== undefined) {
			args.push("--min-score", String(req.minScore));
		}
		const result = await runRunner(args);
		return { result };
	});

	ipcMain.handle("techDebt:getTrend", async (_e, req: ScanRequest) => {
		if (!req.projectPath) throw new Error("projectPath is required");
		const result = await runRunner([
			"--project-path",
			req.projectPath,
			"--command",
			"trend",
		]);
		return { result };
	});

	ipcMain.handle("techDebt:generateSpec", async (_e, req: SpecRequest) => {
		if (!req.projectPath || !req.itemId) {
			throw new Error("projectPath and itemId are required");
		}
		const args = [
			"--project-path",
			req.projectPath,
			"--command",
			"spec",
			"--item-id",
			req.itemId,
		];
		if (req.llmHint) args.push("--llm-hint", req.llmHint);
		const result = await runRunner(args);
		return { result };
	});
}
