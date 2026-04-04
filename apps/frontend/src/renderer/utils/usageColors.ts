import {
	THRESHOLD_CRITICAL,
	THRESHOLD_ELEVATED,
	THRESHOLD_WARNING,
} from "../components/usage/usageConstants";

/**
 * Utility functions for determining usage colors and gradients
 */

/**
 * Returns the appropriate color class based on usage percentage
 */
export function getColorClass(percent: number): string {
	if (percent >= THRESHOLD_CRITICAL) {
		return "text-red-500";
	}
	if (percent >= THRESHOLD_WARNING) {
		return "text-orange-500";
	}
	if (percent >= THRESHOLD_ELEVATED) {
		return "text-yellow-500";
	}
	return "text-green-500";
}

/**
 * Returns the appropriate gradient class based on usage percentage
 */
export function getGradientClass(percent: number): string {
	if (percent >= THRESHOLD_CRITICAL) {
		return "bg-linear-to-r from-red-500 to-red-600";
	}
	if (percent >= THRESHOLD_WARNING) {
		return "bg-linear-to-r from-orange-500 to-orange-600";
	}
	if (percent >= THRESHOLD_ELEVATED) {
		return "bg-linear-to-r from-yellow-500 to-yellow-600";
	}
	return "bg-linear-to-r from-green-500 to-green-600";
}

/**
 * Returns the appropriate background color class for usage indicators
 */
export function getUsageBgColorClass(percent: number): string {
	if (percent >= THRESHOLD_CRITICAL) {
		return "bg-red-500/10";
	}
	if (percent >= THRESHOLD_WARNING) {
		return "bg-orange-500/10";
	}
	if (percent >= THRESHOLD_ELEVATED) {
		return "bg-yellow-500/10";
	}
	return "bg-green-500/10";
}

/**
 * Returns the appropriate border color class for usage indicators
 */
export function getUsageBorderColorClass(percent: number): string {
	if (percent >= THRESHOLD_CRITICAL) {
		return "border-red-500/20";
	}
	if (percent >= THRESHOLD_WARNING) {
		return "border-orange-500/20";
	}
	if (percent >= THRESHOLD_ELEVATED) {
		return "border-yellow-500/20";
	}
	return "border-green-500/20";
}

/**
 * Returns the appropriate text color class for usage indicators
 * Alias for getColorClass for semantic clarity
 */
export function getUsageTextColorClass(percent: number): string {
	return getColorClass(percent);
}

/**
 * Get background/border color classes for badges based on usage percentage
 */
export function getBadgeColorClasses(percent: number): string {
	if (percent >= THRESHOLD_CRITICAL)
		return "text-red-500 bg-red-500/10 border-red-500/20";
	if (percent >= THRESHOLD_WARNING)
		return "text-orange-500 bg-orange-500/10 border-orange-500/20";
	if (percent >= THRESHOLD_ELEVATED)
		return "text-yellow-500 bg-yellow-500/10 border-yellow-500/20";
	return "text-green-500 bg-green-500/10 border-green-500/20";
}

/**
 * Get background class for small usage bars based on usage percentage
 */
export function getBarColorClass(percent: number): string {
	if (percent >= THRESHOLD_CRITICAL) return "bg-red-500";
	if (percent >= THRESHOLD_WARNING) return "bg-orange-500";
	if (percent >= THRESHOLD_ELEVATED) return "bg-yellow-500";
	return "bg-green-500";
}
