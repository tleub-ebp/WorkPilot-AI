/**
 * CLI Tool Types
 *
 * Shared types for CLI tool detection and management.
 * Used by both main process (cli-tool-manager) and renderer process (Settings UI).
 */

/**
 * Result of tool detection operation
 * Contains path, version, and metadata about detection source
 */
export interface ToolDetectionResult {
	found: boolean;
	path?: string;
	version?: string;
	source:
		| "user-config"
		| "venv"
		| "homebrew"
		| "nvm"
		| "system-path"
		| "bundled"
		| "fallback";
	message: string;
}

/**
 * Claude Code CLI version information
 * Used for version checking and update prompts
 */
export interface ClaudeCodeVersionInfo {
	/** Currently installed version, null if not installed */
	installed: string | null;
	/** Latest version available from npm registry */
	latest: string;
	/** True if installed version is older than latest */
	isOutdated: boolean;
	/** Path to Claude CLI binary if found */
	path?: string;
	/** Full detection result with source information */
	detectionResult: ToolDetectionResult;
}

/**
 * Available Claude Code CLI versions
 * Used for version rollback feature
 */
export interface ClaudeCodeVersionList {
	/** List of available versions, sorted newest first */
	versions: string[];
}

/**
 * Information about a detected Claude CLI installation
 * Used for displaying available installations and allowing user selection
 */
export interface ClaudeInstallationInfo {
	/** Full path to the Claude CLI executable */
	path: string;
	/** Version string if detected, null if validation failed */
	version: string | null;
	/** Source of detection (user-config, homebrew, system-path, nvm, etc.) */
	source: ToolDetectionResult["source"];
	/** Whether this is the currently active/configured installation */
	isActive: boolean;
}

/**
 * List of all detected Claude CLI installations
 */
export interface ClaudeInstallationList {
	/** All detected Claude CLI installations */
	installations: ClaudeInstallationInfo[];
	/** Path to the currently active installation (from settings or auto-detected) */
	activePath: string | null;
}

// ============================================
// Copilot CLI Types (mirrors Claude Code CLI)
// ============================================

/**
 * Copilot CLI version information
 * Copilot CLI is a GitHub CLI extension (`gh copilot`), not a standalone executable.
 */
export interface CopilotCliVersionInfo {
	/** Currently installed extension version, null if not installed */
	installed: string | null;
	/** GitHub CLI (gh) version — prerequisite for Copilot */
	ghVersion: string | null;
	/** True if installed version is older than latest */
	isOutdated: boolean;
	/** Path to the `gh` CLI binary (Copilot is invoked via `gh copilot ...`) */
	path?: string;
	/** Full detection result with source information */
	detectionResult: ToolDetectionResult;
}

/**
 * Information about a detected Copilot CLI installation
 */
export interface CopilotInstallationInfo {
	/** Full path to the `gh` CLI executable */
	path: string;
	/** Version of the gh-copilot extension, null if validation failed */
	version: string | null;
	/** Version of the gh CLI host */
	ghVersion: string | null;
	/** Source of detection (user-config, system-path, etc.) */
	source: ToolDetectionResult["source"];
	/** Whether this is the currently active/configured installation */
	isActive: boolean;
}

/**
 * List of all detected Copilot CLI installations
 */
export interface CopilotInstallationList {
	/** All detected Copilot CLI installations (each backed by a `gh` binary) */
	installations: CopilotInstallationInfo[];
	/** Path to the currently active `gh` installation (from settings or auto-detected) */
	activePath: string | null;
}
