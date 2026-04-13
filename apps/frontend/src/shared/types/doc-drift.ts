/**
 * Documentation Drift Detector — Types for doc-code drift detection.
 */

export type DriftType =
	| "stale_reference"
	| "missing_function"
	| "outdated_example"
	| "broken_link"
	| "version_mismatch";

export type DriftSeverity = "high" | "medium" | "low";

export interface DriftIssue {
	driftType: DriftType;
	severity: DriftSeverity;
	docFile: string;
	docLine: number;
	referencedSymbol: string;
	message: string;
	suggestion: string;
}

export interface DriftReport {
	docsScanned: number;
	codeFilesIndexed: number;
	issues: DriftIssue[];
	summary: string;
}
