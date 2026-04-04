/**
 * Session Utilities
 *
 * Handles Claude Code session migration between profiles.
 * Sessions are stored in CLAUDE_CONFIG_DIR/projects/{cwd-path-hash}/{session-id}.jsonl
 * and can be copied between profiles to enable session continuity after profile switches.
 */

import { copyFileSync, cpSync, existsSync, mkdirSync, unlinkSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { isNodeError } from "../utils/type-guards";

/**
 * Convert a working directory path to the Claude projects path format.
 * Claude uses a sanitized path format: /Users/foo/bar -> -Users-foo-bar
 *
 * LIMITATION: This function has a known collision risk where paths containing dashes
 * can collide with paths using directory separators. For example:
 * - '/foo/bar-baz' -> 'foo-bar-baz'
 * - '/foo/bar/baz' -> 'foo-bar-baz'
 *
 * This behavior matches Claude CLI's existing convention for compatibility and is
 * accepted as a low-probability edge case in typical project directory structures.
 *
 * @param cwd - The working directory path to convert
 * @returns The sanitized path format used by Claude for project identification
 */
export function cwdToProjectPath(cwd: string): string {
	// Normalize to forward slashes first (cross-platform: Windows C:\foo\bar -> C:/foo/bar)
	const normalized = cwd.replaceAll("\\", "/");
	// Remove Windows drive letter (C:, D:, etc.) to avoid colons in directory names
	// Then replace all path separators with dashes (keeping leading dash for Unix paths)
	return normalized.replace(/^[a-zA-Z]:/, "").replaceAll("/", "-");
}

/**
 * Get the full path to a session file for a given profile config directory.
 *
 * @param configDir - The profile's CLAUDE_CONFIG_DIR path
 * @param cwd - The working directory where the session was created
 * @param sessionId - The session UUID
 * @returns Full path to the session .jsonl file
 */
export function getSessionFilePath(
	configDir: string,
	cwd: string,
	sessionId: string,
): string {
	const expandedConfigDir = configDir.startsWith("~")
		? configDir.replace(/^~/, homedir())
		: configDir;

	const projectPath = cwdToProjectPath(cwd);
	return join(expandedConfigDir, "projects", projectPath, `${sessionId}.jsonl`);
}

/**
 * Get the full path to a session's tool-results directory.
 *
 * @param configDir - The profile's CLAUDE_CONFIG_DIR path
 * @param cwd - The working directory where the session was created
 * @param sessionId - The session UUID
 * @returns Full path to the session directory (contains tool-results/)
 */
export function getSessionDirPath(
	configDir: string,
	cwd: string,
	sessionId: string,
): string {
	const expandedConfigDir = configDir.startsWith("~")
		? configDir.replace(/^~/, homedir())
		: configDir;

	const projectPath = cwdToProjectPath(cwd);
	return join(expandedConfigDir, "projects", projectPath, sessionId);
}

/**
 * Result of a session migration operation
 */
export interface SessionMigrationResult {
	success: boolean;
	sessionId: string;
	sourceProfile: string;
	targetProfile: string;
	filesCopied: number;
	error?: string;
}

/**
 * Copy the session file with proper error handling.
 */
function copySessionFile(
	sourceFile: string,
	targetFile: string,
): { success: boolean; error?: string; filesCopied: number } {
	try {
		copyFileSync(sourceFile, targetFile);
		console.warn(
			"[SessionUtils] Copied session file:",
			sourceFile,
			"->",
			targetFile,
		);
		return { success: true, filesCopied: 1 };
	} catch (copyError) {
		if (isNodeError(copyError)) {
			if (copyError.code === "ENOENT") {
				return {
					success: false,
					error: `Source session file not found: ${sourceFile}`,
					filesCopied: 0,
				};
			} else if (copyError.code === "EEXIST") {
				console.warn(
					"[SessionUtils] Session already exists in target profile, skipping copy",
				);
				return { success: true, filesCopied: 0 };
			}
		}
		return {
			success: false,
			error: copyError instanceof Error
				? `Failed to copy session file: ${copyError.message}`
				: "Unknown error copying session file",
			filesCopied: 0,
		};
	}
}

/**
 * Copy the session directory (tool-results) if it exists.
 */
function copySessionDirectory(
	sourceDir: string,
	targetDir: string,
): void {
	try {
		cpSync(sourceDir, targetDir, { recursive: true });
		console.warn(
			"[SessionUtils] Copied session directory:",
			sourceDir,
			"->",
			targetDir,
		);
	} catch (dirCopyError) {
		if (isNodeError(dirCopyError) && dirCopyError.code === "ENOENT") {
			console.warn(
				"[SessionUtils] No session directory to copy (this is normal):",
				sourceDir,
			);
		} else {
			console.warn(
				"[SessionUtils] Warning: Failed to copy session directory:",
				dirCopyError instanceof Error
					? dirCopyError.message
					: "Unknown error",
			);
		}
	}
}

/**
 * Clean up partial migration on failure.
 */
function cleanupPartialMigration(targetFile: string): void {
	try {
		unlinkSync(targetFile);
		console.warn(
			"[SessionUtils] Cleaned up partial migration file:",
			targetFile,
		);
	} catch (cleanupError) {
		if (!(isNodeError(cleanupError) && cleanupError.code === "ENOENT")) {
			console.error(
				"[SessionUtils] Failed to cleanup partial migration:",
				cleanupError instanceof Error
					? cleanupError.message
					: "Unknown cleanup error",
			);
		}
	}
}

/**
 * Migrate a Claude Code session from one profile to another.
 *
 * This copies the session .jsonl file and any associated tool-results directory
 * from the source profile's config directory to the target profile's config directory.
 *
 * After migration, the session can be resumed with the target profile's credentials
 * using `claude --resume {sessionId}`.
 *
 * @param sourceConfigDir - Source profile's CLAUDE_CONFIG_DIR
 * @param targetConfigDir - Target profile's CLAUDE_CONFIG_DIR
 * @param cwd - Working directory where the session was created
 * @param sessionId - The session UUID to migrate
 * @returns Migration result with success status and details
 */
export function migrateSession(
	sourceConfigDir: string,
	targetConfigDir: string,
	cwd: string,
	sessionId: string,
): SessionMigrationResult {
	const result: SessionMigrationResult = {
		success: false,
		sessionId,
		sourceProfile: sourceConfigDir,
		targetProfile: targetConfigDir,
		filesCopied: 0,
	};

	const sourceFile = getSessionFilePath(sourceConfigDir, cwd, sessionId);
	const targetFile = getSessionFilePath(targetConfigDir, cwd, sessionId);
	const sourceDir = getSessionDirPath(sourceConfigDir, cwd, sessionId);
	const targetDir = getSessionDirPath(targetConfigDir, cwd, sessionId);

	try {
		const targetParentDir = dirname(targetFile);
		mkdirSync(targetParentDir, { recursive: true });
		console.warn(
			"[SessionUtils] Ensured target directory exists:",
			targetParentDir,
		);

		const fileCopyResult = copySessionFile(sourceFile, targetFile);
		if (!fileCopyResult.success) {
			result.error = fileCopyResult.error;
			console.warn("[SessionUtils] Migration failed:", result.error);
			return result;
		}

		result.filesCopied = fileCopyResult.filesCopied;

		if (fileCopyResult.filesCopied > 0) {
			copySessionDirectory(sourceDir, targetDir);
			result.filesCopied++;
		}

		result.success = true;
		console.warn("[SessionUtils] Session migration successful:", {
			sessionId,
			filesCopied: result.filesCopied,
		});

		return result;
	} catch (error) {
		result.error =
			error instanceof Error ? error.message : "Unknown error during migration";
		console.error("[SessionUtils] Migration error:", result.error);

		cleanupPartialMigration(targetFile);
		return result;
	}
}

/**
 * Check if a session exists in a profile's config directory.
 *
 * @param configDir - The profile's CLAUDE_CONFIG_DIR path
 * @param cwd - The working directory where the session was created
 * @param sessionId - The session UUID to check
 * @returns true if the session file exists
 */
export function sessionExists(
	configDir: string,
	cwd: string,
	sessionId: string,
): boolean {
	const sessionFile = getSessionFilePath(configDir, cwd, sessionId);
	return existsSync(sessionFile);
}
