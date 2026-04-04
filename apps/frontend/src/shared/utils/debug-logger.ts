/**
 * Debug Logger
 * Only logs when DEBUG=true in environment
 *
 * Enhanced with colored logs and scope-based coloring for better readability.
 */

// Import colored logging functions
import {
	frontendDebugLog,
	frontendErrorLog,
	frontendWarningLog,
} from "./frontend-colored-logs";

export const isDebugEnabled = (): boolean => {
	if (typeof process !== "undefined" && process.env) {
		return process.env.DEBUG === "true";
	}
	return false;
};

export const debugLog = (...args: unknown[]): void => {
	if (isDebugEnabled()) {
		frontendDebugLog(args[0] as string, ...args.slice(1));
	}
};

export const debugWarn = (...args: unknown[]): void => {
	if (isDebugEnabled()) {
		frontendWarningLog(args[0] as string, ...args.slice(1));
	}
};

export const debugError = (...args: unknown[]): void => {
	if (isDebugEnabled()) {
		frontendErrorLog(args[0] as string, ...args.slice(1));
	}
};

// Export colored logging functions for direct use
export {
	frontendDebugLog,
	frontendErrorLog,
	frontendWarningLog,
} from "./frontend-colored-logs";
