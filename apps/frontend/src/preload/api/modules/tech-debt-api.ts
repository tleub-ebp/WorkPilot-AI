/**
 * Tech Debt API — renderer-side bridge for the ROI-scored debt dashboard.
 */

import { invokeIpc } from "./ipc-utils";

export type DebtKind =
	| "todo_fixme"
	| "long_function"
	| "deep_complexity"
	| "duplication"
	| "stale_deps"
	| "low_coverage";

export interface DebtItem {
	id: string;
	kind: DebtKind;
	file_path: string;
	line: number;
	message: string;
	cost: number;
	effort: number;
	roi: number;
	tags: string[];
	context: string;
}

export interface DebtTrendPoint {
	timestamp: number;
	total_items: number;
	total_cost: number;
	avg_roi: number;
}

export interface DebtSummary {
	total: number;
	by_kind: Record<string, number>;
	total_cost: number;
	total_effort: number;
	avg_roi: number;
}

export interface DebtReport {
	project_path: string;
	scanned_at: number;
	items: DebtItem[];
	trend: DebtTrendPoint[];
	summary: DebtSummary;
}

export interface DebtListResult {
	items: DebtItem[];
	trend: DebtTrendPoint[];
	summary: DebtSummary;
}

export interface TechDebtAPI {
	scanTechDebt: (options: {
		projectPath: string;
	}) => Promise<{ result: DebtReport }>;
	listDebtItems: (options: {
		projectPath: string;
		minScore?: number;
	}) => Promise<{ result: DebtListResult }>;
	getDebtTrend: (options: {
		projectPath: string;
	}) => Promise<{ result: { trend: DebtTrendPoint[] } }>;
	generateDebtSpec: (options: {
		projectPath: string;
		itemId: string;
		llmHint?: string;
	}) => Promise<{ result: { spec_dir: string } }>;
}

export const createTechDebtAPI = (): TechDebtAPI => ({
	scanTechDebt: (options) =>
		invokeIpc<{ result: DebtReport }>("techDebt:scan", options),
	listDebtItems: (options) =>
		invokeIpc<{ result: DebtListResult }>("techDebt:listItems", options),
	getDebtTrend: (options) =>
		invokeIpc<{ result: { trend: DebtTrendPoint[] } }>(
			"techDebt:getTrend",
			options,
		),
	generateDebtSpec: (options) =>
		invokeIpc<{ result: { spec_dir: string } }>(
			"techDebt:generateSpec",
			options,
		),
});
