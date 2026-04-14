/**
 * Carbon Profiler API
 *
 * Renderer-side bridge to the carbon profiler runner.
 */

import type { CarbonReport } from "../../../shared/types/carbon-profiler";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface CarbonProfilerRunOptions {
	projectPath: string;
	region?: string;
}

export interface CarbonProfilerEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; records?: number };
}

export interface CarbonProfilerAPI {
	runCarbonProfilerScan: (
		options: CarbonProfilerRunOptions,
	) => Promise<CarbonReport>;
	cancelCarbonProfilerScan: () => Promise<boolean>;
	onCarbonProfilerEvent: (
		callback: (event: CarbonProfilerEvent) => void,
	) => () => void;
	onCarbonProfilerResult: (
		callback: (report: CarbonReport) => void,
	) => () => void;
	onCarbonProfilerError: (callback: (error: string) => void) => () => void;
}

export const createCarbonProfilerAPI = (): CarbonProfilerAPI => ({
	runCarbonProfilerScan: (options: CarbonProfilerRunOptions) =>
		invokeIpc<CarbonReport>("carbonProfiler:run", options),

	cancelCarbonProfilerScan: () => invokeIpc<boolean>("carbonProfiler:cancel"),

	onCarbonProfilerEvent: (callback) =>
		createIpcListener<[CarbonProfilerEvent]>("carbon-profiler-event", (payload) =>
			callback(payload),
		),

	onCarbonProfilerResult: (callback) =>
		createIpcListener<[CarbonReport]>("carbon-profiler-result", (payload) =>
			callback(payload),
		),

	onCarbonProfilerError: (callback) =>
		createIpcListener<[string]>("carbon-profiler-error", (payload) =>
			callback(payload),
		),
});
