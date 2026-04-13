/**
 * Accessibility Agent — Types for WCAG compliance scanning.
 */

export type WcagLevel = "A" | "AA" | "AAA";

export type A11ySeverity = "critical" | "serious" | "moderate" | "minor";

export interface A11yViolation {
	ruleId: string;
	description: string;
	severity: A11ySeverity;
	wcagLevel: WcagLevel;
	wcagCriteria: string;
	file: string;
	line: number;
	element: string;
	suggestion: string;
}

export interface A11yReport {
	filesScanned: number;
	targetLevel: WcagLevel;
	violations: A11yViolation[];
	passedRules: string[];
	summary: string;
}
