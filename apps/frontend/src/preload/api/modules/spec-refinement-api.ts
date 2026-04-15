/**
 * Spec Refinement API
 *
 * Renderer-side bridge to the spec refinement runner which discovers
 * persisted refinement histories in the selected project.
 */

import type { RefinementHistory } from "../../../shared/types/spec-refinement";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface SpecRefinementRunOptions {
	projectPath: string;
}

export interface SpecRefinementResult {
	histories: RefinementHistory[];
}

export interface SpecRefinementEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; histories?: number };
}

export interface SpecRefinementAPI {
	runSpecRefinementScan: (
		options: SpecRefinementRunOptions,
	) => Promise<SpecRefinementResult>;
	cancelSpecRefinementScan: () => Promise<boolean>;
	onSpecRefinementEvent: (
		callback: (event: SpecRefinementEvent) => void,
	) => () => void;
	onSpecRefinementResult: (
		callback: (result: SpecRefinementResult) => void,
	) => () => void;
	onSpecRefinementError: (callback: (error: string) => void) => () => void;
}

export const createSpecRefinementAPI = (): SpecRefinementAPI => ({
	runSpecRefinementScan: (options: SpecRefinementRunOptions) =>
		invokeIpc<SpecRefinementResult>("specRefinement:run", options),

	cancelSpecRefinementScan: () => invokeIpc<boolean>("specRefinement:cancel"),

	onSpecRefinementEvent: (callback) =>
		createIpcListener<[SpecRefinementEvent]>("spec-refinement-event", (payload) =>
			callback(payload),
		),

	onSpecRefinementResult: (callback) =>
		createIpcListener<[SpecRefinementResult]>("spec-refinement-result", (payload) =>
			callback(payload),
		),

	onSpecRefinementError: (callback) =>
		createIpcListener<[string]>("spec-refinement-error", (payload) =>
			callback(payload),
		),
});
