/**
 * Injection Guard API
 *
 * Renderer-side bridge to the injection guard runner which scans persisted
 * prompt payloads for prompt injection attempts.
 */

import type { InjectionScanResult } from "../../../shared/types/injection-guard";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface InjectionGuardRunOptions {
	projectPath: string;
}

export interface InjectionGuardScanResult {
	results: InjectionScanResult[];
}

export interface InjectionGuardEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; results?: number };
}

export interface InjectionGuardAPI {
	runInjectionGuardScan: (
		options: InjectionGuardRunOptions,
	) => Promise<InjectionGuardScanResult>;
	cancelInjectionGuardScan: () => Promise<boolean>;
	onInjectionGuardEvent: (
		callback: (event: InjectionGuardEvent) => void,
	) => () => void;
	onInjectionGuardResult: (
		callback: (result: InjectionGuardScanResult) => void,
	) => () => void;
	onInjectionGuardError: (
		callback: (error: string) => void,
	) => () => void;
}

export const createInjectionGuardAPI = (): InjectionGuardAPI => ({
	runInjectionGuardScan: (options: InjectionGuardRunOptions) =>
		invokeIpc<InjectionGuardScanResult>("injectionGuard:run", options),

	cancelInjectionGuardScan: () => invokeIpc<boolean>("injectionGuard:cancel"),

	onInjectionGuardEvent: (callback) =>
		createIpcListener<[InjectionGuardEvent]>(
			"injection-guard-event",
			(payload) => callback(payload),
		),

	onInjectionGuardResult: (callback) =>
		createIpcListener<[InjectionGuardScanResult]>(
			"injection-guard-result",
			(payload) => callback(payload),
		),

	onInjectionGuardError: (callback) =>
		createIpcListener<[string]>("injection-guard-error", (payload) =>
			callback(payload),
		),
});
