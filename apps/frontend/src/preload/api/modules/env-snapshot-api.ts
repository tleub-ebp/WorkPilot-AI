/**
 * Environment Snapshot API — renderer-side bridge.
 */

import { invokeIpc } from "./ipc-utils";

export type EnvSnapshotFormat = "dockerfile" | "nix" | "script";

export interface EnvSnapshotLockfile {
	name: string;
	sha256: string | null;
	size: string;
}

export interface EnvSnapshot {
	id: string;
	createdAt: string;
	label: string;
	specId: string | null;
	os: {
		system: string;
		release: string;
		version: string;
		machine: string;
		python: string;
	};
	tools: Record<string, string | null>;
	lockfiles: EnvSnapshotLockfile[];
	git: {
		commit: string;
		branch: string;
		remote: string;
		dirty: string[];
	};
	env: Record<string, string>;
}

export interface EnvSnapshotAPI {
	captureEnvSnapshot: (args: {
		projectPath: string;
		specId?: string;
		label?: string;
	}) => Promise<{ snapshot: EnvSnapshot }>;
	listEnvSnapshots: (projectPath: string) => Promise<{ snapshots: EnvSnapshot[] }>;
	getEnvSnapshot: (
		projectPath: string,
		snapId: string,
	) => Promise<{ snapshot: EnvSnapshot }>;
	replayEnvSnapshot: (
		projectPath: string,
		snapId: string,
		format: EnvSnapshotFormat,
	) => Promise<{ payload: string; format: EnvSnapshotFormat }>;
	exportEnvSnapshot: (
		projectPath: string,
		snapId: string,
		format: EnvSnapshotFormat,
	) => Promise<{ path: string; format: EnvSnapshotFormat }>;
}

export const createEnvSnapshotAPI = (): EnvSnapshotAPI => ({
	captureEnvSnapshot: (args) => invokeIpc("envSnapshot:capture", args),
	listEnvSnapshots: (projectPath) =>
		invokeIpc("envSnapshot:list", { projectPath }),
	getEnvSnapshot: (projectPath, snapId) =>
		invokeIpc("envSnapshot:get", { projectPath, snapId }),
	replayEnvSnapshot: (projectPath, snapId, format) =>
		invokeIpc("envSnapshot:replay", { projectPath, snapId, format }),
	exportEnvSnapshot: (projectPath, snapId, format) =>
		invokeIpc("envSnapshot:export", { projectPath, snapId, format }),
});
