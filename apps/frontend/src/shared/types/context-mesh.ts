/**
 * Types for the Context Mesh — Cross-Project Intelligence feature.
 */

export type PatternCategory =
	| "architecture"
	| "auth"
	| "api_design"
	| "state_management"
	| "testing"
	| "deployment"
	| "error_handling"
	| "security"
	| "performance"
	| "naming_convention"
	| "project_structure"
	| "database"
	| "logging"
	| "ci_cd"
	| "other";

export type HandbookDomain =
	| "auth"
	| "api_design"
	| "state_management"
	| "testing"
	| "deployment"
	| "security"
	| "performance"
	| "database"
	| "frontend"
	| "backend"
	| "devops"
	| "general";

export type RecommendationType =
	| "pattern_reuse"
	| "convention_adoption"
	| "bug_prevention"
	| "divergence_alert"
	| "complexity_estimate"
	| "skill_transfer";

export interface ProjectSummary {
	project_path: string;
	project_name: string;
	registered_at: string;
	last_analyzed_at: string;
	pattern_count: number;
	tech_stack: string[];
	frameworks: string[];
	languages: string[];
}

export interface CrossProjectPattern {
	pattern_id: string;
	category: PatternCategory;
	title: string;
	description: string;
	source_projects: string[];
	target_projects: string[];
	confidence: number;
	occurrence_count: number;
	code_example: string;
	migration_hint: string;
	first_seen: string;
	last_seen: string;
	applied_count: number;
	dismissed_count: number;
	adoption_rate: number;
}

export interface HandbookEntry {
	entry_id: string;
	domain: HandbookDomain;
	title: string;
	description: string;
	decision_rationale: string;
	source_projects: string[];
	related_commits: string[];
	related_prs: string[];
	code_examples: string[];
	tags: string[];
	created_at: string;
	updated_at: string;
	version: number;
}

export interface SkillTransfer {
	transfer_id: string;
	skill_name: string;
	description: string;
	source_project: string;
	target_projects: string[];
	category: PatternCategory;
	framework_or_api: string;
	convention_details: string;
	confidence: number;
	status: "pending" | "accepted" | "dismissed";
	created_at: string;
}

export interface ContextualRecommendation {
	recommendation_id: string;
	recommendation_type: RecommendationType;
	title: string;
	description: string;
	source_project: string;
	target_project: string;
	relevance_score: number;
	phase: string;
	related_pattern_id: string;
	action_suggestion: string;
	created_at: string;
	status: "active" | "applied" | "dismissed" | "expired";
}

export interface ContextMeshConfig {
	enabled: boolean;
	auto_analyze: boolean;
	analyze_on_build_complete: boolean;
	cross_project_suggestions: boolean;
	handbook_generation: boolean;
	skill_transfer: boolean;
	max_projects: number;
	min_confidence_threshold: number;
}

export interface MeshAnalysisReport {
	analyzed_projects: string[];
	patterns_found: CrossProjectPattern[];
	handbook_entries: HandbookEntry[];
	skill_transfers: SkillTransfer[];
	recommendations: ContextualRecommendation[];
	generated_at: string;
	analysis_model: string;
}

export interface ContextMeshSummary {
	project_count: number;
	pattern_count: number;
	handbook_entry_count: number;
	skill_transfer_count: number;
	recommendation_count: number;
	active_recommendations: number;
	pending_transfers: number;
	projects: Array<{ name: string; path: string }>;
}

export interface ContextMeshCompleteResult {
	report: MeshAnalysisReport;
	summary: ContextMeshSummary;
}
