/**
 * Release Coordinator API
 *
 * Renderer-side bridge to the release coordinator runner.
 */

import type { ReleaseTrainPlan } from "../../../shared/types/release-coordinator";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface ReleaseCoordinatorRunOptions {
	projectPath: string;
	maxCommits?: number;
}

export interface ReleaseCoordinatorEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; services?: number };
}

export interface ReleaseCoordinatorAPI {
	runReleaseCoordinatorPlan: (
		options: ReleaseCoordinatorRunOptions,
	) => Promise<ReleaseTrainPlan>;
	cancelReleaseCoordinatorPlan: () => Promise<boolean>;
	onReleaseCoordinatorEvent: (
		callback: (event: ReleaseCoordinatorEvent) => void,
	) => () => void;
	onReleaseCoordinatorResult: (
		callback: (plan: ReleaseTrainPlan) => void,
	) => () => void;
	onReleaseCoordinatorError: (
		callback: (error: string) => void,
	) => () => void;
}

export const createReleaseCoordinatorAPI = (): ReleaseCoordinatorAPI => ({
	runReleaseCoordinatorPlan: (options: ReleaseCoordinatorRunOptions) =>
		invokeIpc<ReleaseTrainPlan>("releaseCoordinator:run", options),

	cancelReleaseCoordinatorPlan: () =>
		invokeIpc<boolean>("releaseCoordinator:cancel"),

	onReleaseCoordinatorEvent: (callback) =>
		createIpcListener<[ReleaseCoordinatorEvent]>(
			"release-coordinator-event",
			(payload) => callback(payload),
		),

	onReleaseCoordinatorResult: (callback) =>
		createIpcListener<[ReleaseTrainPlan]>(
			"release-coordinator-result",
			(payload) => callback(payload),
		),

	onReleaseCoordinatorError: (callback) =>
		createIpcListener<[string]>("release-coordinator-error", (payload) =>
			callback(payload),
		),
});
