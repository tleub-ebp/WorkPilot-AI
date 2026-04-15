/**
 * API Watcher API
 *
 * Renderer-side bridge to the api watcher runner.
 */

import type { ContractDiff } from "../../../shared/types/api-watcher";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface ApiWatcherRunOptions {
	projectPath: string;
	saveBaseline?: boolean;
}

export interface ApiWatcherResult {
	diff: ContractDiff;
	migrationGuideMarkdown: string;
	summary: string;
}

export interface ApiWatcherEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; breaking?: number };
}

export interface ApiWatcherAPI {
	runApiWatcherScan: (
		options: ApiWatcherRunOptions,
	) => Promise<ApiWatcherResult>;
	cancelApiWatcherScan: () => Promise<boolean>;
	onApiWatcherEvent: (
		callback: (event: ApiWatcherEvent) => void,
	) => () => void;
	onApiWatcherResult: (
		callback: (result: ApiWatcherResult) => void,
	) => () => void;
	onApiWatcherError: (callback: (error: string) => void) => () => void;
}

export const createApiWatcherAPI = (): ApiWatcherAPI => ({
	runApiWatcherScan: (options: ApiWatcherRunOptions) =>
		invokeIpc<ApiWatcherResult>("apiWatcher:run", options),

	cancelApiWatcherScan: () => invokeIpc<boolean>("apiWatcher:cancel"),

	onApiWatcherEvent: (callback) =>
		createIpcListener<[ApiWatcherEvent]>("api-watcher-event", (payload) =>
			callback(payload),
		),

	onApiWatcherResult: (callback) =>
		createIpcListener<[ApiWatcherResult]>("api-watcher-result", (payload) =>
			callback(payload),
		),

	onApiWatcherError: (callback) =>
		createIpcListener<[string]>("api-watcher-error", (payload) =>
			callback(payload),
		),
});
