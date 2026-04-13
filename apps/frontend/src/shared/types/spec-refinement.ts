/**
 * Incremental Spec Refinement — Types for iterative spec improvement.
 */

export type SignalType =
	| "qa_failure"
	| "review_comment"
	| "user_edit"
	| "cost_overrun"
	| "test_failure"
	| "security_violation"
	| "performance_regression"
	| "lint_error";

export type RefinementStatus =
	| "draft"
	| "refining"
	| "converged"
	| "diverging"
	| "abandoned";

export interface FeedbackSignal {
	signalType: SignalType;
	source: string;
	message: string;
	severity: string;
	timestamp: string;
}

export interface RefinementIteration {
	iteration: number;
	signals: FeedbackSignal[];
	changesMade: string[];
	qualityScore: number;
	timestamp: string;
}

export interface RefinementHistory {
	specId: string;
	iterations: RefinementIteration[];
	status: RefinementStatus;
	convergenceScore: number;
	currentIteration: number;
	isConverging: boolean;
	summary: string;
}
