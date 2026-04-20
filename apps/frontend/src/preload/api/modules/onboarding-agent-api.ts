/**
 * Onboarding Agent API
 *
 * Renderer-side bridge to the onboarding agent runner.
 */

import type { OnboardingGuide } from "../../../shared/types/onboarding";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface OnboardingAgentRunOptions {
	projectPath: string;
}

export interface OnboardingTourStep {
	order: number;
	title: string;
	file_path: string;
	reason: string;
	suggested_questions: string[];
}

export interface OnboardingQuizQuestion {
	question: string;
	choices: string[];
	correct_index: number;
	rationale: string;
}

export interface OnboardingFirstTask {
	title: string;
	file_path: string;
	line: number;
	source_comment: string;
}

export interface OnboardingGlossaryTerm {
	term: string;
	occurrences: number;
	sources: string[];
}

export interface OnboardingPackage {
	guide: {
		project_name: string;
		tech_stack: string[];
		key_files: Array<{ path: string; reason: string }>;
		conventions: Array<{ name: string; description: string }>;
		sections: Record<string, string>;
		estimated_reading_time_min: number;
	};
	tour: OnboardingTourStep[];
	quiz: OnboardingQuizQuestion[];
	first_tasks: OnboardingFirstTask[];
	glossary: OnboardingGlossaryTerm[];
}

export interface OnboardingAgentResult {
	guide: OnboardingGuide;
	package?: OnboardingPackage;
}

export interface OnboardingAgentEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; steps?: number };
}

export interface OnboardingAgentAPI {
	runOnboardingAgentScan: (
		options: OnboardingAgentRunOptions,
	) => Promise<OnboardingAgentResult>;
	cancelOnboardingAgentScan: () => Promise<boolean>;
	onOnboardingAgentEvent: (
		callback: (event: OnboardingAgentEvent) => void,
	) => () => void;
	onOnboardingAgentResult: (
		callback: (result: OnboardingAgentResult) => void,
	) => () => void;
	onOnboardingAgentError: (callback: (error: string) => void) => () => void;
}

export const createOnboardingAgentAPI = (): OnboardingAgentAPI => ({
	runOnboardingAgentScan: (options: OnboardingAgentRunOptions) =>
		invokeIpc<OnboardingAgentResult>("onboardingAgent:run", options),

	cancelOnboardingAgentScan: () =>
		invokeIpc<boolean>("onboardingAgent:cancel"),

	onOnboardingAgentEvent: (callback) =>
		createIpcListener<[OnboardingAgentEvent]>("onboarding-event", (payload) =>
			callback(payload),
		),

	onOnboardingAgentResult: (callback) =>
		createIpcListener<[OnboardingAgentResult]>("onboarding-result", (payload) =>
			callback(payload),
		),

	onOnboardingAgentError: (callback) =>
		createIpcListener<[string]>("onboarding-error", (payload) =>
			callback(payload),
		),
});
