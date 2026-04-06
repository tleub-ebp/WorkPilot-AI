#!/usr/bin/env node

/**
 * Merge Upstream Script
 *
 * This script provides a cross-platform way to merge changes from upstream
 * into your fork using npm/pnpm.
 *
 * Usage:
 *   pnpm merge-upstream
 *   pnpm merge-upstream -- --skip-push
 *   pnpm merge-upstream -- --branch main
 */

const { execSync } = require("node:child_process");
const os = require("node:os");
const path = require("node:path");
const fs = require("node:fs");

const isWindows = os.platform() === "win32";
const rootDir = path.resolve(__dirname, "..");

console.log("\n🚀 WorkPilot AI Upstream Merge Tool\n");

// Determine which script to run
let scriptPath;
let command;

if (isWindows) {
	// Try PowerShell first (more feature-rich)
	try {
		execSync(
			'powershell -NoProfile -Command "Get-ExecutionPolicy -Scope CurrentUser" 2>&1',
			{
				stdio: "pipe",
				encoding: "utf-8",
			},
		);

		scriptPath = path.join(rootDir, "merge-upstream.ps1");
		// Build PowerShell command with proper argument handling
		const args = process.argv.slice(2);
		let psArgs = "";
		for (const arg of args) {
			if (arg === "--skip-push") {
				psArgs += " -SkipPush";
			} else if (arg === "--branch" && args[args.indexOf(arg) + 1]) {
				const nextIdx = args.indexOf(arg) + 1;
				psArgs += ` -Branch "${args[nextIdx]}"`;
				args.splice(nextIdx, 1); // Remove next arg to avoid duplication
			}
		}

		command = `powershell -NoProfile -ExecutionPolicy Bypass -File "${scriptPath}"${psArgs}`;
	} catch (_e) {
		// Fall back to batch
		scriptPath = path.join(rootDir, "merge-upstream.bat");
		command = `"${scriptPath}"`;
	}
} else {
	// Unix-like systems
	scriptPath = path.join(rootDir, "merge-upstream.sh");
	const args = process.argv.slice(2).join(" ");
	command = `bash "${scriptPath}" ${args}`;
}

// Verify script exists
if (!fs.existsSync(scriptPath)) {
	console.error(`❌ Error: Script not found at ${scriptPath}`);
	console.error(
		`Please ensure merge-upstream scripts are in the repository root.`,
	);
	process.exit(1);
}

console.log(`📝 Running: ${path.basename(scriptPath)}\n`);

try {
	execSync(command, {
		stdio: "inherit",
		shell: isWindows ? "cmd.exe" : "/bin/bash",
	});
	process.exit(0);
} catch (error) {
	process.exit(error.status || 1);
}
