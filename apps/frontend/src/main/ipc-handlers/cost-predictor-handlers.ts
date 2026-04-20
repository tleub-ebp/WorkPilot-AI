/**
 * Cost Predictor IPC Handlers
 *
 * Spawns apps/backend/runners/cost_predictor_runner.py to produce an
 * ex-ante cost prediction before a spec is executed.
 *
 * Channels:
 *   invoke "costPredictor:run" → { projectPath, specId, provider, model, compare? }
 *     → { report }
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { app, ipcMain } from "electron";
import { pythonEnvManager } from "../python-env-manager.js";

interface PredictRequest {
	projectPath: string;
	specId: string;
	provider?: string;
	model?: string;
	compare?: string;
	thinking?: boolean;
}

interface PredictResponse {
	report: unknown;
}

export function registerCostPredictorHandlers(): void {
	ipcMain.handle(
		"costPredictor:run",
		async (_event, req: PredictRequest): Promise<PredictResponse> => {
			if (!req.projectPath || !req.specId) {
				throw new Error("projectPath and specId are required");
			}

			const backendPath = app.isPackaged
				? path.resolve(process.resourcesPath, "backend")
				: path.resolve(app.getAppPath(), "..", "backend");
			const runnerPath = path.resolve(
				backendPath,
				"runners",
				"cost_predictor_runner.py",
			);

			const pythonExe = pythonEnvManager.getPythonPath();
			if (!pythonExe) throw new Error("Python environment not ready");

			const args = [
				runnerPath,
				"--project-path",
				req.projectPath,
				"--spec-id",
				req.specId,
				"--provider",
				req.provider ?? "anthropic",
				"--model",
				req.model ?? "claude-sonnet-4-6",
			];
			if (req.compare) {
				args.push("--compare", req.compare);
			}
			if (req.thinking === false) {
				args.push("--no-thinking");
			}

			return await new Promise<PredictResponse>((resolve, reject) => {
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
									`cost_predictor_runner exited with ${code}: ${stderr}`,
								),
							);
							return;
						}
						resolve({ report: parsed.report });
					} catch (err) {
						reject(
							new Error(
								`Failed to parse predictor output: ${(err as Error).message} (stdout=${stdout.slice(0, 200)})`,
							),
						);
					}
				});
			});
		},
	);
}
