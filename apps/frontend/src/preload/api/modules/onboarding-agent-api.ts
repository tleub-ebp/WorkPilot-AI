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

export interface OnboardingAgentResult {
	guide: OnboardingGuide;
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
