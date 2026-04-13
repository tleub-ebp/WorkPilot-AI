/**
 * i18n Agent — Types for internationalisation scanning.
 */

export type I18nIssueType =
	| "hardcoded_string"
	| "missing_key"
	| "unused_key"
	| "inconsistent_interpolation"
	| "missing_plural";

export type I18nSeverity = "error" | "warning" | "info";

export interface I18nIssue {
	issueType: I18nIssueType;
	severity: I18nSeverity;
	file: string;
	line: number;
	key: string;
	locale: string;
	message: string;
	suggestion: string;
}

export interface I18nReport {
	filesScanned: number;
	localesCompared: string[];
	issues: I18nIssue[];
	coverageByLocale: Record<string, number>;
	summary: string;
}
