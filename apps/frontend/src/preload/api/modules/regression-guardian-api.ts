/**
 * Regression Guardian API
 *
 * Renderer-side bridge to the regression guardian runner which turns
 * persisted APM incident payloads into regression test candidates.
 */

import type { RegressionGuardianResult } from "../../../shared/types/regression-guardian";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface RegressionGuardianRunOptions {
	projectPath: string;
}

export interface RegressionGuardianScanResult {
	results: RegressionGuardianResult[];
}

export interface RegressionGuardianEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; results?: number };
}

export interface RegressionGuardianAPI {
	runRegressionGuardianScan: (
		options: RegressionGuardianRunOptions,
	) => Promise<RegressionGuardianScanResult>;
	cancelRegressionGuardianScan: () => Promise<boolean>;
	onRegressionGuardianEvent: (
		callback: (event: RegressionGuardianEvent) => void,
	) => () => void;
	onRegressionGuardianResult: (
		callback: (result: RegressionGuardianScanResult) => void,
	) => () => void;
	onRegressionGuardianError: (
		callback: (error: string) => void,
	) => () => void;
}

export const createRegressionGuardianAPI = (): RegressionGuardianAPI => ({
	runRegressionGuardianScan: (options: RegressionGuardianRunOptions) =>
		invokeIpc<RegressionGuardianScanResult>(
			"regressionGuardian:run",
			options,
		),

	cancelRegressionGuardianScan: () =>
		invokeIpc<boolean>("regressionGuardian:cancel"),

	onRegressionGuardianEvent: (callback) =>
		createIpcListener<[RegressionGuardianEvent]>(
			"regression-guardian-event",
			(payload) => callback(payload),
		),

	onRegressionGuardianResult: (callback) =>
		createIpcListener<[RegressionGuardianScanResult]>(
			"regression-guardian-result",
			(payload) => callback(payload),
		),

	onRegressionGuardianError: (callback) =>
		createIpcListener<[string]>("regression-guardian-error", (payload) =>
			callback(payload),
		),
});
