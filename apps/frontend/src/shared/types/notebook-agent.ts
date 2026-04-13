/**
 * Notebook Agent — Types for Jupyter notebook handling.
 */

export type CellType = "code" | "markdown" | "raw";

export type NotebookIssueType =
	| "stale_output"
	| "out_of_order"
	| "missing_import"
	| "empty_cell"
	| "long_cell"
	| "no_markdown"
	| "sensitive_output";

export interface NotebookCell {
	index: number;
	cellType: CellType;
	source: string;
	executionCount: number | null;
	outputCount: number;
}

export interface NotebookIssue {
	issueType: NotebookIssueType;
	cellIndex: number;
	message: string;
	severity: string;
	suggestion: string;
}

export interface ParsedNotebook {
	path: string;
	kernel: string;
	language: string;
	totalCells: number;
	codeCells: number;
	markdownCells: number;
	issues: NotebookIssue[];
}
