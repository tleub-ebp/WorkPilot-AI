/**
 * Doc Drift API
 *
 * Renderer-side bridge to the documentation drift scanner runner.
 */

import type { DriftReport } from "../../../shared/types/doc-drift";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface DocDriftRunOptions {
	projectPath: string;
}

export interface DocDriftEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; issues?: number; docsScanned?: number };
}

export interface DocDriftAPI {
	runDocDriftScan: (options: DocDriftRunOptions) => Promise<DriftReport>;
	cancelDocDriftScan: () => Promise<boolean>;
	onDocDriftEvent: (callback: (event: DocDriftEvent) => void) => () => void;
	onDocDriftResult: (callback: (report: DriftReport) => void) => () => void;
	onDocDriftError: (callback: (error: string) => void) => () => void;
}

export const createDocDriftAPI = (): DocDriftAPI => ({
	runDocDriftScan: (options: DocDriftRunOptions) =>
		invokeIpc<DriftReport>("docDrift:run", options),

	cancelDocDriftScan: () => invokeIpc<boolean>("docDrift:cancel"),

	onDocDriftEvent: (callback) =>
		createIpcListener<[DocDriftEvent]>("doc-drift-event", (payload) =>
			callback(payload),
		),

	onDocDriftResult: (callback) =>
		createIpcListener<[DriftReport]>("doc-drift-result", (payload) =>
			callback(payload),
		),

	onDocDriftError: (callback) =>
		createIpcListener<[string]>("doc-drift-error", (payload) =>
			callback(payload),
		),
});
