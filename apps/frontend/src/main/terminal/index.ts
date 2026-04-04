/**
 * Terminal Module
 * Modular terminal management system with Claude integration
 */

// Claude integration utilities
export * as ClaudeIntegration from "./claude-integration-handler";
// Output parsing utilities
export * as OutputParser from "./output-parser";
// PTY management utilities
export * as PtyManager from "./pty-manager";
// Session management utilities
export * as SessionHandler from "./session-handler";
// Event handler utilities
export * as TerminalEventHandler from "./terminal-event-handler";
// Terminal lifecycle utilities
export * as TerminalLifecycle from "./terminal-lifecycle";
// Main manager
export { TerminalManager } from "./terminal-manager";
// Types
export type {
	OAuthTokenEvent,
	RateLimitEvent,
	SessionCaptureResult,
	TerminalOperationResult,
	TerminalProcess,
	WindowGetter,
} from "./types";
