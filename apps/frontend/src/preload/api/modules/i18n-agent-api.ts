/**
 * i18n Agent API
 *
 * Renderer-side bridge to the i18n scanner runner.
 */

import type { I18nReport } from "../../../shared/types/i18n-agent";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface I18nAgentRunOptions {
	projectPath: string;
	referenceLocale?: string;
}

export interface I18nAgentEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; issues?: number; filesScanned?: number };
}

export interface I18nAgentAPI {
	runI18nScan: (options: I18nAgentRunOptions) => Promise<I18nReport>;
	cancelI18nScan: () => Promise<boolean>;
	onI18nAgentEvent: (
		callback: (event: I18nAgentEvent) => void,
	) => () => void;
	onI18nAgentResult: (
		callback: (report: I18nReport) => void,
	) => () => void;
	onI18nAgentError: (callback: (error: string) => void) => () => void;
}

export const createI18nAgentAPI = (): I18nAgentAPI => ({
	runI18nScan: (options: I18nAgentRunOptions) =>
		invokeIpc<I18nReport>("i18nAgent:run", options),

	cancelI18nScan: () => invokeIpc<boolean>("i18nAgent:cancel"),

	onI18nAgentEvent: (callback) =>
		createIpcListener<[I18nAgentEvent]>("i18n-agent-event", (payload) =>
			callback(payload),
		),

	onI18nAgentResult: (callback) =>
		createIpcListener<[I18nReport]>("i18n-agent-result", (payload) =>
			callback(payload),
		),

	onI18nAgentError: (callback) =>
		createIpcListener<[string]>("i18n-agent-error", (payload) =>
			callback(payload),
		),
});
