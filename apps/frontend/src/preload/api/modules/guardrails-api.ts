/**
 * Guardrails API — renderer-side bridge for user-defined agent guardrails.
 */

import { invokeIpc } from "./ipc-utils";

export type GuardrailAction = "allow" | "warn" | "deny" | "require_approval";

export interface GuardrailRuleDoc {
	id: string;
	description: string;
	action: GuardrailAction;
	when: {
		tool?: string | string[];
		path_prefix?: string;
		path_regex?: string;
		content_regex?: string;
		command_pattern?: string;
		content_max_lines?: number;
		content_max_bytes?: number;
		forbidden_strings?: string[];
	};
}

export interface GuardrailsDoc {
	version: number;
	rules: GuardrailRuleDoc[];
}

export interface GuardrailTestResult {
	action: GuardrailAction;
	triggered: string[];
	message: string;
}

export interface GuardrailsAPI {
	loadGuardrails: (projectPath: string) => Promise<GuardrailsDoc>;
	saveGuardrails: (projectPath: string, doc: GuardrailsDoc) => Promise<boolean>;
	testGuardrails: (
		projectPath: string,
		toolName: string,
		toolInput: Record<string, unknown>,
	) => Promise<GuardrailTestResult>;
}

export const createGuardrailsAPI = (): GuardrailsAPI => ({
	loadGuardrails: (projectPath) =>
		invokeIpc<GuardrailsDoc>("guardrails:load", { projectPath }),
	saveGuardrails: (projectPath, doc) =>
		invokeIpc<boolean>("guardrails:save", { projectPath, doc }),
	testGuardrails: (projectPath, toolName, toolInput) =>
		invokeIpc<GuardrailTestResult>("guardrails:test", {
			projectPath,
			toolName,
			toolInput,
		}),
});
