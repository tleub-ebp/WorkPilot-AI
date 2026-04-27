/**
 * Type definitions for the Codebase Longevity Score backend module.
 * Mirrors `apps/backend/longevity/scorer.py`.
 */

export type HealthGrade = "A" | "B" | "C" | "D" | "F";

export interface LongevityProjection {
	weeks_observed: number;
	current_score: number;
	projected_score_in_6_months: number;
	projected_grade_in_6_months: HealthGrade;
	direction: "improving" | "stable" | "degrading";
	weekly_delta: number;
}

export interface RiskiestFile {
	file_path: string;
	items: number;
	total_cost: number;
	kinds: string[];
}

export interface LongevitySummary {
	loc: number;
	total_debt_items: number;
	by_kind: Record<string, number>;
}

export interface LongevityReport {
	project_path: string;
	score: number;
	grade: HealthGrade;
	penalties: Record<string, number>;
	bonuses: Record<string, number>;
	summary: LongevitySummary;
	projection: LongevityProjection | null;
	riskiest_files: RiskiestFile[];
}

export interface LongevityScoreResult {
	success: boolean;
	report?: LongevityReport;
	error?: string;
}
