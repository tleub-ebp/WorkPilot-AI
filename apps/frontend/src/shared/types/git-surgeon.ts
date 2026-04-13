/**
 * Git History Surgeon — Types for history analysis and cleanup.
 */

export type HistoryIssueType =
	| "large_blob"
	| "sensitive_data"
	| "messy_commits"
	| "force_push_risk"
	| "duplicate_commits";

export type SurgeryAction =
	| "squash"
	| "reword"
	| "drop"
	| "bfg_remove"
	| "filter_branch";

export interface HistoryIssue {
	issueType: HistoryIssueType;
	severity: string;
	description: string;
	commitSha: string;
	filePath: string;
	sizeBytes: number;
	suggestedAction: SurgeryAction;
}

export interface SurgeryPlan {
	issues: HistoryIssue[];
	actions: Array<{ action: SurgeryAction; description: string }>;
	estimatedSizeSavingsMb: number;
	requiresForcePush: boolean;
	summary: string;
}
