/**
 * Bounty Board IPC Handlers
 *
 * Spawns apps/backend/runners/bounty_board_runner.py to run a competitive
 * multi-agent round. The backend is provider-agnostic — callers pass
 * contestants as `provider:model` pairs.
 *
 * Channels:
 *   invoke "bountyBoard:start"        → { projectPath, specId, contestants[], profiles?[], promptOverrides?[] } → { result }
 *   invoke "bountyBoard:listArchives" → { projectPath, specId } → { archives: BountyResult[] }
 */

import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { app, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface ContestantInput {
	provider: string;
	model: string;
	profileId?: string;
	promptOverride?: string;
}

interface StartRequest {
	projectPath: string;
	specId: string;
	contestants: ContestantInput[];
}

interface ListArchivesRequest {
	projectPath: string;
	specId: string;
}

interface StartResponse {
	result: unknown;
}

function resolveBackendPaths(): { backendPath: string; runnerPath: string } {
	const backendPath = app.isPackaged
		? path.resolve(process.resourcesPath, "backend")
		: path.resolve(app.getAppPath(), "..", "backend");
	const runnerPath = path.resolve(
		backendPath,
		"runners",
		"bounty_board_runner.py",
	);
	return { backendPath, runnerPath };
}

function resolveSpecDir(projectPath: string, specId: string): string {
	const candidates = [
		path.join(projectPath, ".workpilot", "specs", specId),
		path.join(projectPath, ".autonomousbuild", "specs", specId),
	];
	for (const c of candidates) {
		if (fs.existsSync(c)) return c;
	}
	return candidates[0];
}

export function registerBountyBoardHandlers(): void {
	ipcMain.handle(
		"bountyBoard:start",
		async (_event, req: StartRequest): Promise<StartResponse> => {
			if (!req.projectPath || !req.specId) {
				throw new Error("projectPath and specId are required");
			}
			if (!Array.isArray(req.contestants) || req.contestants.length === 0) {
				throw new Error("At least one contestant is required");
			}

			const { backendPath, runnerPath } = resolveBackendPaths();
			const pythonExe = pythonEnvManager.getPythonPath();
			if (!pythonExe) throw new Error("Python environment not ready");

			const contestantsArg = req.contestants
				.map((c) => `${c.provider}:${c.model}`)
				.join(",");
			const profilesArg = req.contestants
				.map((c) => c.profileId ?? "")
				.join(",");
			const overridesArg = req.contestants
				.map((c) => (c.promptOverride ?? "").replace(/\|\|/g, "|"))
				.join("||");

			const args = [
				runnerPath,
				"--project-path",
				req.projectPath,
				"--spec-id",
				req.specId,
				"--contestants",
				contestantsArg,
			];
			if (profilesArg.replaceAll(/,/g, "").length > 0) {
				args.push("--profiles", profilesArg);
			}
			if (overridesArg.replaceAll(/\|/g, "").length > 0) {
				args.push("--prompt-overrides", overridesArg);
			}

			return await new Promise<StartResponse>((resolve, reject) => {
				const child = spawn(pythonExe, args, {
					cwd: backendPath,
					env: { ...process.env, PYTHONPATH: backendPath },
				} as Parameters<typeof spawn>[2]);

				let stdout = "";
				let stderr = "";
				child.stdout?.on("data", (chunk: Buffer) => {
					stdout += chunk.toString();
				});
				child.stderr?.on("data", (chunk: Buffer) => {
					stderr += chunk.toString();
				});
				child.on("error", (err) => reject(err));
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
									`bounty_board_runner exited with ${code}: ${stderr}`,
								),
							);
							return;
						}
						resolve({ result: parsed.result });
					} catch (err) {
						reject(
							new Error(
								`Failed to parse runner output: ${(err as Error).message} (stdout=${stdout.slice(0, 200)})`,
							),
						);
					}
				});
			});
		},
	);

	ipcMain.handle(
		"bountyBoard:listArchives",
		async (
			_event,
			req: ListArchivesRequest,
		): Promise<{ archives: unknown[] }> => {
			if (!req.projectPath || !req.specId) {
				return { archives: [] };
			}
			const specDir = resolveSpecDir(req.projectPath, req.specId);
			const bountyDir = path.join(specDir, "bounty");
			if (!fs.existsSync(bountyDir)) return { archives: [] };

			const files = fs
				.readdirSync(bountyDir)
				.filter((f) => f.endsWith(".json"))
				.sort()
				.reverse();

			const archives: unknown[] = [];
			for (const f of files) {
				try {
					const raw = fs.readFileSync(path.join(bountyDir, f), "utf-8");
					archives.push(JSON.parse(raw));
				} catch {
					// skip malformed
				}
			}
			return { archives };
		},
	);
}
