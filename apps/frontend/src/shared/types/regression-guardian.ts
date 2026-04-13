/**
 * Regression Guardian — Types for incident-to-test pipeline.
 */

export type IncidentSource =
	| "sentry"
	| "datadog"
	| "cloudwatch"
	| "new_relic"
	| "pagerduty"
	| "grafana"
	| "opsgenie"
	| "generic";

export type IncidentSeverity = "info" | "warning" | "error" | "critical";

export type TestFramework =
	| "pytest"
	| "jest"
	| "vitest"
	| "mocha"
	| "junit5"
	| "go_test"
	| "xunit"
	| "cargo_test";

export interface StackFrame {
	file: string;
	function: string;
	line: number;
	column: number;
	context: string;
}

export interface Incident {
	id: string;
	source: IncidentSource;
	title: string;
	severity: IncidentSeverity;
	exceptionType: string;
	exceptionMessage: string;
	stackFrames: StackFrame[];
	service: string;
	environment: string;
	faultingFile: string | null;
	faultingFunction: string | null;
}

export interface GeneratedTest {
	incidentId: string;
	framework: TestFramework;
	filePath: string;
	code: string;
	isDuplicate: boolean;
}

export interface RegressionGuardianResult {
	incident: Incident;
	generatedTest: GeneratedTest | null;
	isDuplicate: boolean;
	duplicatePath: string;
	fixtureData: Record<string, unknown>;
}
