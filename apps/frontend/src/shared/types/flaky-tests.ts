/**
 * Flaky Test Detective — Types for flaky test analysis.
 */

export type FlakyCause =
	| "timing"
	| "network"
	| "shared_state"
	| "concurrency"
	| "resource_leak"
	| "randomness"
	| "environment"
	| "unknown";

export type FlakyConfidence = "high" | "medium" | "low";

export interface FlakyTest {
	testName: string;
	totalRuns: number;
	failures: number;
	flakinessRate: number;
	probableCause: FlakyCause;
	confidence: FlakyConfidence;
	errorPatterns: string[];
	suggestedFix: string;
}

export interface FlakyReport {
	totalTests: number;
	flakyCount: number;
	flakyTests: FlakyTest[];
	summary: string;
}
