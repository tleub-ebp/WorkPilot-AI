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
import { getPathDelimiter } from "../platform/index.js";
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

	// Convert absolute target paths to relative paths if needed
	// Also auto-detect project root if targets are outside the specified root
	const resolvedProjectRoot = path.resolve(projectRoot);
	const resolvedTargets = targets.map((t) => path.resolve(t));

	// Check if all targets are under the specified project root
	const allUnderRoot = resolvedTargets.every((t) =>
		t.startsWith(resolvedProjectRoot),
	);

	let effectiveProjectRoot = projectRoot;
	let relativeTargets: string[];

	if (!allUnderRoot) {
		// Find common ancestor of all target files to use as project root
		if (resolvedTargets.length === 1) {
			// Single target: use its parent directory
			effectiveProjectRoot = path.dirname(resolvedTargets[0]);
		} else {
			// Multiple targets: find common ancestor
			const commonPath = resolvedTargets.reduce((common, current) => {
				const commonParts = common.split(path.sep);
				const currentParts = current.split(path.sep);
				const minLength = Math.min(commonParts.length, currentParts.length);
				const newCommon: string[] = [];
				for (let i = 0; i < minLength; i++) {
					if (commonParts[i] === currentParts[i]) {
						newCommon.push(commonParts[i]);
					} else {
						break;
					}
				}
				return newCommon.join(path.sep);
			}, resolvedTargets[0]);
			effectiveProjectRoot = commonPath || path.dirname(resolvedTargets[0]);
		}
	}

	// Convert targets to relative paths from the effective project root
	const resolvedEffectiveRoot = path.resolve(effectiveProjectRoot);
	relativeTargets = resolvedTargets.map((target) => {
		if (target.startsWith(resolvedEffectiveRoot)) {
			return path.relative(resolvedEffectiveRoot, target);
		}
		// If still not under root, keep as-is
		return target;
	});

	const args = [
		runnerPath,
		"--project-root",
		effectiveProjectRoot,
		"--targets",
		relativeTargets.join(","),
	];

	return new Promise((resolve, reject) => {
		// Add paths to PYTHONPATH so Python can find the apps module
		// The script imports from apps.backend.project, so we need the parent of apps in PYTHONPATH
		const parentPath = path.dirname(backendPath); // apps directory
		const repoRoot = path.dirname(parentPath); // parent of apps (repo root)
		const env = pythonEnvManager.getPythonEnv();
		const currentPythonPath = env.PYTHONPATH || "";
		const pathDelimiter = getPathDelimiter();
		env.PYTHONPATH = currentPythonPath
			? `${backendPath}${pathDelimiter}${parentPath}${pathDelimiter}${repoRoot}${pathDelimiter}${currentPythonPath}`
			: `${backendPath}${pathDelimiter}${parentPath}${pathDelimiter}${repoRoot}`;

		const child = spawn(pythonExe, args, {
			cwd: backendPath,
			env,
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
			if (lines.length === 0) {
				reject(
					new Error(
						`blast-radius runner produced no output. Exit code: ${code}. Stderr: ${stderr || "(empty)"}`,
					),
				);
				return;
			}
			const last = lines.pop() ?? "";
			try {
				const parsed = JSON.parse(last) as Record<string, unknown>;
				if (parsed.error) {
					const errorMessage =
						typeof parsed.error === "string"
							? parsed.error
							: JSON.stringify(parsed.error);
					reject(new Error(errorMessage));
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
						`Failed to parse blast-radius runner output: ${(err as Error).message}. Last line: ${last}`,
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
