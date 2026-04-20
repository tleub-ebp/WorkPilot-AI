/**
 * Team Bot IPC Handlers — Slack / Microsoft Teams notifications.
 *
 * Channels:
 *   teamBot:send → { config, payload } → { ok }
 *   teamBot:test → { config }          → { ok }
 *
 * Provider-agnostic: no LLM calls, only outbound webhook POSTs.
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { app, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

function runRunner(
	action: "send" | "test",
	payload: Record<string, unknown>,
): Promise<unknown> {
	const backendPath = app.isPackaged
		? path.resolve(process.resourcesPath, "backend")
		: path.resolve(app.getAppPath(), "..", "backend");
	const runnerPath = path.resolve(
		backendPath,
		"runners",
		"team_bot_runner.py",
	);
	const pythonExe = pythonEnvManager.getPythonPath();
	if (!pythonExe) return Promise.reject(new Error("Python env not ready"));

	const args = [
		runnerPath,
		"--action",
		action,
		"--payload",
		JSON.stringify(payload),
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
				if (code !== 0 && code !== 2) {
					reject(new Error(`runner exit ${code}: ${stderr}`));
					return;
				}
				resolve(parsed);
			} catch (err) {
				reject(
					new Error(
						`Failed to parse team-bot runner output: ${(err as Error).message}`,
					),
				);
			}
		});
	});
}

export function registerTeamBotHandlers(): void {
	ipcMain.handle(
		"teamBot:send",
		async (
			_e,
			{
				config,
				payload,
			}: { config: Record<string, unknown>; payload: Record<string, unknown> },
		) => runRunner("send", { config, payload }),
	);
	ipcMain.handle(
		"teamBot:test",
		async (_e, { config }: { config: Record<string, unknown> }) =>
			runRunner("test", { config }),
	);
}
