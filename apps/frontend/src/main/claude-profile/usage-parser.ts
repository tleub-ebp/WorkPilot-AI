/**
 * Usage Parser Module
 * Handles parsing of Claude /usage command output and reset time calculations
 */

import type { ClaudeUsageData } from "../../shared/types";

/**
 * Regex to parse /usage command output
 * Matches patterns like: "████▌ 9% used" and "Resets Nov 1, 10:59am (America/Sao_Paulo)"
 */
const USAGE_PERCENT_PATTERN = /(\d+)%\s*used/i;
const USAGE_RESET_PATTERN = /Resets?\s+(.+?)(?:\s*$|\n)/i;

/**
 * Convert 12-hour format to 24-hour format
 */
function convertTo24Hour(hour: number, ampm: string): number {
	if (ampm.toLowerCase() === "pm" && hour < 12) hour += 12;
	if (ampm.toLowerCase() === "am" && hour === 12) hour = 0;
	return hour;
}

/**
 * Create month mapping for date parsing
 */
function getMonthMap(): Record<string, number> {
	return {
		jan: 0,
		feb: 1,
		mar: 2,
		apr: 3,
		may: 4,
		jun: 5,
		jul: 6,
		aug: 7,
		sep: 8,
		oct: 9,
		nov: 10,
		dec: 11,
	};
}

/**
 * Parse date-time string with month and day
 */
function parseDateTimeWithMonth(resetTimeStr: string, now: Date): Date | null {
	const dateRegex = /([A-Za-z]+)\s+(\d+)(?:,|\s+at)?\s*(\d+)?:?(\d+)?(am|pm)?/i;
	const dateMatch = dateRegex.exec(resetTimeStr);
	if (!dateMatch) return null;

	const [, month, day, hour = "0", minute = "0", ampm = ""] = dateMatch;
	const monthMap = getMonthMap();
	const monthNum = monthMap[month.toLowerCase()] ?? now.getMonth();
	const hourNum = convertTo24Hour(Number.parseInt(hour, 10), ampm);

	const resetDate = new Date(
		now.getFullYear(),
		monthNum,
		Number.parseInt(day, 10),
		hourNum,
		Number.parseInt(minute, 10),
	);

	// If the date is in the past, assume next year
	if (resetDate < now) {
		resetDate.setFullYear(resetDate.getFullYear() + 1);
	}
	return resetDate;
}

/**
 * Parse time-only string (no date)
 */
function parseTimeOnly(resetTimeStr: string, now: Date): Date | null {
	const timeOnlyRegex = /(\d+):?(\d+)?\s*(am|pm)/i;
	const timeOnlyMatch = timeOnlyRegex.exec(resetTimeStr);
	if (!timeOnlyMatch) return null;

	const [, hour, minute = "0", ampm] = timeOnlyMatch;
	const hourNum = convertTo24Hour(Number.parseInt(hour, 10), ampm);

	const resetDate = new Date(
		now.getFullYear(),
		now.getMonth(),
		now.getDate(),
		hourNum,
		Number.parseInt(minute, 10),
	);

	// If the time is in the past, assume tomorrow
	if (resetDate < now) {
		resetDate.setDate(resetDate.getDate() + 1);
	}
	return resetDate;
}

/**
 * Create fallback date when parsing fails
 */
function createFallbackDate(resetTimeStr: string, now: Date): Date {
	const isWeekly =
		resetTimeStr.toLowerCase().includes("week") ||
		/[a-z]{3}\s+\d+/i.test(resetTimeStr); // Has a date like "Dec 17"

	if (isWeekly) {
		return new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
	}
	return new Date(now.getTime() + 5 * 60 * 60 * 1000);
}

/**
 * Parse a rate limit reset time string and estimate when it resets
 * Examples: "Dec 17 at 6am (Europe/Oslo)", "11:59pm (America/Sao_Paulo)", "Nov 1, 10:59am"
 */
export function parseResetTime(resetTimeStr: string): Date {
	const now = new Date();

	// Try to parse date-time format first
	const dateTimeResult = parseDateTimeWithMonth(resetTimeStr, now);
	if (dateTimeResult) return dateTimeResult;

	// Try to parse time-only format
	const timeOnlyResult = parseTimeOnly(resetTimeStr, now);
	if (timeOnlyResult) return timeOnlyResult;

	// Fallback to estimated time
	return createFallbackDate(resetTimeStr, now);
}

/**
 * Determine if a rate limit is session-based or weekly based on reset time
 */
export function classifyRateLimitType(
	resetTimeStr: string,
): "session" | "weekly" {
	// Weekly limits mention specific dates like "Dec 17" or "Nov 1"
	// Session limits are typically just times like "11:59pm"
	const hasDate = /[A-Za-z]{3}\s+\d+/i.test(resetTimeStr);
	const hasWeeklyIndicator = resetTimeStr.toLowerCase().includes("week");

	return hasDate || hasWeeklyIndicator ? "weekly" : "session";
}

/**
 * Parse Claude /usage command output into structured data
 * Expected format sections:
 * "Current session ████▌ 9% used Resets 11:59pm"
 * "Current week (all models) 79% used Resets Nov 1, 10:59am"
 * "Current week (Opus) 0% used"
 */
export function parseUsageOutput(usageOutput: string): ClaudeUsageData {
	const sections = usageOutput.split(/Current\s+/i).filter(Boolean);
	const usage: ClaudeUsageData = {
		sessionUsagePercent: 0,
		sessionResetTime: "",
		weeklyUsagePercent: 0,
		weeklyResetTime: "",
		lastUpdated: new Date(),
	};

	for (const section of sections) {
		const percentMatch = USAGE_PERCENT_PATTERN.exec(section);
		const resetMatch = USAGE_RESET_PATTERN.exec(section);

		if (percentMatch) {
			const percent = Number.parseInt(percentMatch[1], 10);
			const resetTime = resetMatch?.[1]?.trim() || "";

			if (/session/i.test(section)) {
				usage.sessionUsagePercent = percent;
				usage.sessionResetTime = resetTime;
			} else if (/week.*all\s*model/i.test(section)) {
				usage.weeklyUsagePercent = percent;
				usage.weeklyResetTime = resetTime;
			} else if (/week.*opus/i.test(section)) {
				usage.opusUsagePercent = percent;
			}
		}
	}

	return usage;
}
