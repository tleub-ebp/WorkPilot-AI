/**
 * API Contract Watcher — Types for contract diff and migration guides.
 */

export type ContractFormat = "openapi" | "graphql" | "protobuf" | "unknown";

export type ChangeCategory =
	| "breaking"
	| "potentially_breaking"
	| "non_breaking";

export type ChangeType =
	| "endpoint_removed"
	| "endpoint_added"
	| "endpoint_deprecated"
	| "parameter_added_required"
	| "parameter_removed"
	| "type_removed"
	| "type_added"
	| "field_removed"
	| "field_added"
	| "field_type_changed"
	| "field_required_added";

export interface ContractChange {
	changeType: ChangeType;
	category: ChangeCategory;
	path: string;
	description: string;
	oldValue?: string;
	newValue?: string;
}

export interface ContractDiff {
	oldVersion: string;
	newVersion: string;
	format: ContractFormat;
	changes: ContractChange[];
	breakingCount: number;
	potentiallyBreakingCount: number;
	nonBreakingCount: number;
}

export interface MigrationGuide {
	markdown: string;
	breakingChanges: ContractChange[];
	generatedAt: string;
}
