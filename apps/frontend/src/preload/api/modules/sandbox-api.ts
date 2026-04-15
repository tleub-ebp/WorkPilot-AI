/**
 * Sandbox API
 *
 * Renderer-side bridge to the sandbox runner which produces a dry-run
 * simulation result of uncommitted changes.
 */

import type { SimulationResult } from "../../../shared/types/sandbox";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface SandboxRunOptions {
	projectPath: string;
}

export interface SandboxResult {
	result: SimulationResult;
}

export interface SandboxEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; files?: number; additions?: number; deletions?: number };
}

export interface SandboxAPI {
	runSandboxScan: (options: SandboxRunOptions) => Promise<SandboxResult>;
	cancelSandboxScan: () => Promise<boolean>;
	onSandboxEvent: (callback: (event: SandboxEvent) => void) => () => void;
	onSandboxResult: (callback: (result: SandboxResult) => void) => () => void;
	onSandboxError: (callback: (error: string) => void) => () => void;
}

export const createSandboxAPI = (): SandboxAPI => ({
	runSandboxScan: (options: SandboxRunOptions) =>
		invokeIpc<SandboxResult>("sandbox:run", options),

	cancelSandboxScan: () => invokeIpc<boolean>("sandbox:cancel"),

	onSandboxEvent: (callback) =>
		createIpcListener<[SandboxEvent]>("sandbox-event", (payload) =>
			callback(payload),
		),

	onSandboxResult: (callback) =>
		createIpcListener<[SandboxResult]>("sandbox-result", (payload) =>
			callback(payload),
		),

	onSandboxError: (callback) =>
		createIpcListener<[string]>("sandbox-error", (payload) => callback(payload)),
});
