/**
 * Git Surgeon API
 *
 * Renderer-side bridge to the git surgeon runner.
 */

import type { SurgeryPlan } from "../../../shared/types/git-surgeon";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface GitSurgeonRunOptions {
	projectPath: string;
	maxCommits?: number;
}

export interface GitSurgeonEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; issues?: number; savingsMb?: number };
}

export interface GitSurgeonAPI {
	runGitSurgeonScan: (options: GitSurgeonRunOptions) => Promise<SurgeryPlan>;
	cancelGitSurgeonScan: () => Promise<boolean>;
	onGitSurgeonEvent: (
		callback: (event: GitSurgeonEvent) => void,
	) => () => void;
	onGitSurgeonResult: (
		callback: (plan: SurgeryPlan) => void,
	) => () => void;
	onGitSurgeonError: (callback: (error: string) => void) => () => void;
}

export const createGitSurgeonAPI = (): GitSurgeonAPI => ({
	runGitSurgeonScan: (options: GitSurgeonRunOptions) =>
		invokeIpc<SurgeryPlan>("gitSurgeon:run", options),

	cancelGitSurgeonScan: () => invokeIpc<boolean>("gitSurgeon:cancel"),

	onGitSurgeonEvent: (callback) =>
		createIpcListener<[GitSurgeonEvent]>("git-surgeon-event", (payload) =>
			callback(payload),
		),

	onGitSurgeonResult: (callback) =>
		createIpcListener<[SurgeryPlan]>("git-surgeon-result", (payload) =>
			callback(payload),
		),

	onGitSurgeonError: (callback) =>
		createIpcListener<[string]>("git-surgeon-error", (payload) =>
			callback(payload),
		),
});
