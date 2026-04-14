/**
 * Flaky Tests API
 *
 * Renderer-side bridge to the flaky tests runner.
 */

import type { FlakyReport } from "../../../shared/types/flaky-tests";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface FlakyTestsRunOptions {
	projectPath: string;
}

export interface FlakyTestsEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; flakyCount?: number; totalTests?: number };
}

export interface FlakyTestsAPI {
	runFlakyTestsScan: (options: FlakyTestsRunOptions) => Promise<FlakyReport>;
	cancelFlakyTestsScan: () => Promise<boolean>;
	onFlakyTestsEvent: (
		callback: (event: FlakyTestsEvent) => void,
	) => () => void;
	onFlakyTestsResult: (
		callback: (report: FlakyReport) => void,
	) => () => void;
	onFlakyTestsError: (callback: (error: string) => void) => () => void;
}

export const createFlakyTestsAPI = (): FlakyTestsAPI => ({
	runFlakyTestsScan: (options: FlakyTestsRunOptions) =>
		invokeIpc<FlakyReport>("flakyTests:run", options),

	cancelFlakyTestsScan: () => invokeIpc<boolean>("flakyTests:cancel"),

	onFlakyTestsEvent: (callback) =>
		createIpcListener<[FlakyTestsEvent]>("flaky-tests-event", (payload) =>
			callback(payload),
		),

	onFlakyTestsResult: (callback) =>
		createIpcListener<[FlakyReport]>("flaky-tests-result", (payload) =>
			callback(payload),
		),

	onFlakyTestsError: (callback) =>
		createIpcListener<[string]>("flaky-tests-error", (payload) =>
			callback(payload),
		),
});
