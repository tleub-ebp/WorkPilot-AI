/**
 * Agent Simulation Sandbox — Types for dry-run simulation.
 */

export type SandboxPhase =
	| "idle"
	| "creating_worktree"
	| "running_simulation"
	| "analyzing_diff"
	| "awaiting_approval"
	| "complete"
	| "error";

export type StepStatus = "success" | "warning" | "error" | "skipped";

export type ApprovalDecision = "approved" | "rejected" | "partial";

export interface MockResponse {
	url: string;
	method: string;
	statusCode: number;
	body: string;
	strategy: "schema_based" | "llm_generated" | "static" | "error";
}

export interface SimulationStep {
	index: number;
	description: string;
	status: StepStatus;
	durationMs: number;
	tokensUsed: number;
	mockApiCalls: MockResponse[];
	warnings: string[];
	errors: string[];
}

export interface FileDiff {
	filePath: string;
	changeType: "added" | "modified" | "deleted" | "renamed";
	additions: number;
	deletions: number;
	hunks: DiffHunk[];
}

export interface DiffHunk {
	oldStart: number;
	oldCount: number;
	newStart: number;
	newCount: number;
	content: string;
}

export interface SimulationResult {
	id: string;
	specId: string;
	phase: SandboxPhase;
	steps: SimulationStep[];
	diffs: FileDiff[];
	totalTokensUsed: number;
	estimatedCostUsd: number;
	estimatedRealCostUsd: number;
	durationMs: number;
	successCount: number;
	warningCount: number;
	errorCount: number;
	createdAt: string;
}

export interface ApprovalResult {
	decision: ApprovalDecision;
	approvedFiles: string[];
	rejectedFiles: string[];
	comment: string;
}
