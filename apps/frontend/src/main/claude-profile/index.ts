/**
 * Claude Profile Module
 * Central export point for all profile management functionality
 */

export type {
	ProfileScoreParams,
	TimeToLimitData,
	VelocityData,
} from "./profile-scorer";
// Profile scoring and auto-switch
export {
	calculateProfileScore,
	getBestAvailableProfile,
	getProfilesSortedByAvailability,
	shouldProactivelySwitch,
} from "./profile-scorer";
// Profile selection lock (anti-race condition)
export {
	getProfileSelectionLock,
	resetProfileSelectionLock,
} from "./profile-selection-lock";
export type { ProfileStoreData } from "./profile-storage";

// Storage utilities
export {
	DEFAULT_AUTO_SWITCH_SETTINGS,
	loadProfileStore,
	STORE_VERSION,
	saveProfileStore,
} from "./profile-storage";
// Profile utilities
export {
	CLAUDE_PROFILES_DIR,
	createProfileDirectory,
	DEFAULT_CLAUDE_CONFIG_DIR,
	expandHomePath,
	generateProfileId,
	hasValidToken,
	isProfileAuthenticated,
} from "./profile-utils";
// Rate limit management
export {
	clearRateLimitEvents,
	isProfileRateLimited,
	recordRateLimitEvent,
} from "./rate-limit-manager";
// Token encryption utilities
export {
	decryptToken,
	encryptToken,
	isTokenEncrypted,
} from "./token-encryption";
// Core types
export type {
	ClaudeAutoSwitchSettings,
	ClaudeProfile,
	ClaudeProfileSettings,
	ClaudeRateLimitEvent,
	ClaudeUsageData,
} from "./types";
// Usage monitoring (proactive account switching)
export { getUsageMonitor, UsageMonitor } from "./usage-monitor";
// Usage parsing utilities
export {
	classifyRateLimitType,
	parseResetTime,
	parseUsageOutput,
} from "./usage-parser";
// Velocity tracking (predictive switching)
export { getVelocityTracker, resetVelocityTracker } from "./velocity-tracker";
