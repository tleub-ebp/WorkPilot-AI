/**
 * Shared fixtures for integration tests that need an on-disk
 * `auto-claude-source` layout — the minimum that ``getAutoBuildSourcePath``
 * and the subprocess spawn codepath expect to find.
 *
 * Used by:
 *   src/__tests__/integration/subprocess-spawn.test.ts
 *
 * Why this lives in a helper: the fs scaffolding is pure logic and
 * safe to share. Electron / child_process mocks must stay inline in
 * each test file because `vi.mock` calls are hoisted and cannot be
 * set from a helper that runs at normal import time.
 */

import {
	existsSync,
	mkdirSync,
	mkdtempSync,
	rmSync,
	writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

export interface AutoClaudeFixture {
	/** Root temp directory — remove this to clean everything up. */
	testDir: string;
	/** Dummy project path the agent is spawned against. */
	projectPath: string;
	/** Dummy auto-claude source path — contains spec_runner.py + run.py. */
	autoClaudeSource: string;
}

/**
 * Create a fresh temp-dir layout with the dummy source files the
 * subprocess spawn code scans for. Returns paths + a cleanup fn.
 */
export function createAutoClaudeFixture(
	prefix = "subprocess-spawn-test-",
): AutoClaudeFixture {
	const testDir = mkdtempSync(path.join(tmpdir(), prefix));
	const projectPath = path.join(testDir, "test-project");
	const autoClaudeSource = path.join(testDir, "auto-claude-source");

	mkdirSync(projectPath, { recursive: true });
	mkdirSync(autoClaudeSource, { recursive: true });
	mkdirSync(path.join(autoClaudeSource, "runners"), { recursive: true });

	writeFileSync(
		path.join(autoClaudeSource, "runners", "spec_runner.py"),
		'# Mock spec runner\nprint("Starting spec creation")',
	);
	writeFileSync(
		path.join(autoClaudeSource, "run.py"),
		'# Mock run.py\nprint("Starting task execution")',
	);

	return { testDir, projectPath, autoClaudeSource };
}

/** Best-effort cleanup — no-op if the directory is already gone. */
export function cleanupAutoClaudeFixture(fixture: AutoClaudeFixture): void {
	if (fixture.testDir && existsSync(fixture.testDir)) {
		rmSync(fixture.testDir, { recursive: true, force: true });
	}
}
