/**
 * Types for the Live Development Companion feature.
 */

export type SuggestionType =
	| "bug_detection"
	| "duplicate_code"
	| "missing_update"
	| "contract_violation"
	| "performance_issue"
	| "security_issue"
	| "missing_test"
	| "refactor_opportunity"
	| "import_suggestion"
	| "convention_mismatch"
	| "general";

export type SuggestionPriority =
	| "critical"
	| "high"
	| "medium"
	| "low"
	| "info";

export type TakeoverStatus =
	| "proposed"
	| "accepted"
	| "declined"
	| "in_progress"
	| "completed"
	| "cancelled";

export interface FileChangeEvent {
	file_path: string;
	change_type: "created" | "modified" | "deleted" | "renamed";
	diff: string;
	language: string;
	timestamp: string;
}

export interface LiveSuggestion {
	suggestion_id: string;
	suggestion_type: SuggestionType;
	priority: SuggestionPriority;
	title: string;
	description: string;
	file_path: string;
	line_start: number;
	line_end: number;
	code_fix: string;
	related_files: string[];
	confidence: number;
	created_at: string;
	status: "active" | "applied" | "dismissed" | "expired";
}

export interface TakeoverProposal {
	proposal_id: string;
	file_path: string;
	reason: string;
	description: string;
	inactivity_seconds: number;
	complexity_score: number;
	status: TakeoverStatus;
	ai_plan: string;
	ai_result_summary: string;
	created_at: string;
}

export interface CompanionConfig {
	enabled: boolean;
	watch_debounce_ms: number;
	suggestion_enabled: boolean;
	takeover_enabled: boolean;
	takeover_inactivity_seconds: number;
	min_suggestion_confidence: number;
	max_suggestions_per_file: number;
	watch_patterns: string[];
	ignore_patterns: string[];
}

export interface CompanionState {
	active: boolean;
	watching_project: string;
	files_watched: number;
	changes_detected: number;
	suggestions_generated: number;
	suggestions_accepted: number;
	takeovers_proposed: number;
	takeovers_accepted: number;
	started_at: string;
	last_change_at: string;
}
