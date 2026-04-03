#!/usr/bin/env node

/**
 * Upstream Sync Configuration Validator
 *
 * Checks that all upstream sync tools are properly set up and configured.
 * Usage: node scripts/validate-upstream-setup.js
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const ROOT_DIR = path.resolve(__dirname, "..");
const COLORS = {
	reset: "\x1b[0m",
	green: "\x1b[32m",
	red: "\x1b[31m",
	yellow: "\x1b[33m",
	blue: "\x1b[34m",
	cyan: "\x1b[36m",
};

class Validator {
	constructor() {
		this.checks = [];
		this.passed = 0;
		this.failed = 0;
	}

	log(message, level = "info") {
		const colors = {
			info: COLORS.cyan,
			success: COLORS.green,
			error: COLORS.red,
			warning: COLORS.yellow,
			debug: COLORS.blue,
		};
		const color = colors[level] || colors.info;
		console.log(`${color}${message}${COLORS.reset}`);
	}

	check(name, condition, errorMessage) {
		if (condition) {
			this.log(`✓ ${name}`, "success");
			this.passed++;
		} else {
			this.log(`✗ ${name}`, "error");
			if (errorMessage) this.log(`  → ${errorMessage}`, "warning");
			this.failed++;
		}
	}

	run() {
		console.log(`\n${COLORS.cyan}${"=".repeat(50)}${COLORS.reset}`);
		console.log(`${COLORS.cyan}Upstream Sync Setup Validator${COLORS.reset}`);
		console.log(`${COLORS.cyan}${"=".repeat(50)}${COLORS.reset}\n`);

		// 1. Check files exist
		this.log("📋 Checking required files...", "info");
		const requiredFiles = [
			"merge-upstream.ps1",
			"merge-upstream.bat",
			"merge-upstream.sh",
			"scripts/merge-upstream.js",
			"MERGE_UPSTREAM.md",
			"GIT_SETUP.md",
			"QUICK_REFERENCE.md",
			".github/workflows/sync-upstream.yml",
		];

		requiredFiles.forEach((file) => {
			const fullPath = path.join(ROOT_DIR, file);
			const exists = fs.existsSync(fullPath);
			this.check(`${file}`, exists, exists ? "" : "File not found");
		});

		console.log("");

		// 2. Check git configuration
		this.log("🔧 Checking Git configuration...", "info");
		try {
			const remotes = execSync("git remote -v", {
				cwd: ROOT_DIR,
				encoding: "utf-8",
			});

			const hasOrigin = remotes.includes("origin");
			const hasUpstream = remotes.includes("upstream") || true; // Upstream is optional initially

			this.check(
				"origin remote exists",
				hasOrigin,
				"Please configure origin remote",
			);

			if (hasOrigin && remotes.includes("github.com/tleub-ebp/WorkPilot-AI")) {
				this.check("origin points to fork (tleub-ebp)", true);
			} else if (hasOrigin) {
				this.log("  ⚠ origin points to different URL", "warning");
			}
		} catch (e) {
			this.check(
				"git configured",
				false,
				"Git not available or not configured",
			);
		}

		console.log("");

		// 3. Check scripts are executable
		this.log("🔐 Checking script permissions...", "info");
		const executableScripts = [
			"merge-upstream.sh",
			"scripts/merge-upstream.js",
		];

		executableScripts.forEach((script) => {
			const fullPath = path.join(ROOT_DIR, script);
			if (fs.existsSync(fullPath)) {
				try {
					const stats = fs.statSync(fullPath);
					const isExecutable = (stats.mode & 0o111) !== 0;
					this.check(
						`${script} is executable`,
						isExecutable,
						"Run: chmod +x " + script,
					);
				} catch (e) {
					this.log(`  ⚠ Could not check ${script} permissions`, "warning");
				}
			}
		});

		console.log("");

		// 4. Check package.json has merge-upstream script
		this.log("📦 Checking package.json...", "info");
		try {
			const pkgPath = path.join(ROOT_DIR, "package.json");
			const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));
			const hasMergeScript = pkg.scripts && pkg.scripts["merge-upstream"];
			this.check("merge-upstream script in package.json", hasMergeScript);
		} catch (e) {
			this.log("  ⚠ Could not read package.json", "warning");
		}

		console.log("");

		// 5. Check documentation links
		this.log("📚 Checking documentation...", "info");
		try {
			const readmePath = path.join(ROOT_DIR, "README.md");
			const readme = fs.readFileSync(readmePath, "utf-8");

			const hasMergeRef = readme.includes("merge-upstream");
			const hasSync = readme.includes("Syncing with Upstream");

			this.check("README mentions upstream sync", hasMergeRef || hasSync);
		} catch (e) {
			this.log("  ⚠ Could not check README.md", "warning");
		}

		console.log("");

		// Summary
		console.log(`${COLORS.cyan}${"=".repeat(50)}${COLORS.reset}`);
		console.log(`${COLORS.cyan}Summary${COLORS.reset}`);
		console.log(`${COLORS.cyan}${"=".repeat(50)}${COLORS.reset}\n`);

		const total = this.passed + this.failed;
		const percentage = total > 0 ? Math.round((this.passed / total) * 100) : 0;

		console.log(`Passed: ${COLORS.green}${this.passed}${COLORS.reset}`);
		console.log(
			`Failed: ${this.failed > 0 ? COLORS.red : COLORS.green}${this.failed}${COLORS.reset}`,
		);
		console.log(`Total:  ${total}`);
		console.log(`Score:  ${percentage}%`);
		console.log("");

		if (this.failed === 0) {
			this.log(
				"✓ All checks passed! Upstream sync is properly configured.",
				"success",
			);
			this.log("Run: pnpm merge-upstream", "info");
		} else {
			this.log(
				`✗ ${this.failed} check(s) failed. Please review the errors above.`,
				"error",
			);
		}

		console.log("");

		return this.failed === 0 ? 0 : 1;
	}
}

const validator = new Validator();
const exitCode = validator.run();
process.exit(exitCode);
