/**
 * Personal Agent Coach — Types for agent performance coaching.
 */

export type TipCategory =
	| "prompt_engineering"
	| "cost_optimisation"
	| "workflow"
	| "error_prevention"
	| "performance"
	| "best_practice";

export type TipPriority = "high" | "medium" | "low";

export interface CoachTip {
	category: TipCategory;
	priority: TipPriority;
	title: string;
	description: string;
	evidence: string;
	action: string;
}

export interface AgentRunRecord {
	agentName: string;
	runId: string;
	success: boolean;
	durationS: number;
	tokensUsed: number;
	costUsd: number;
	errors: string[];
	retries: number;
	model: string;
	timestamp: string;
}

export interface CoachReport {
	tips: CoachTip[];
	totalRuns: number;
	successRate: number;
	avgCostUsd: number;
	totalCostUsd: number;
	mostUsedModel: string;
	mostFailingAgent: string;
	summary: string;
}
