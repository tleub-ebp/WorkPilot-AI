/**
 * Offline Mode API — renderer-side bridge.
 */

import { invokeIpc } from "./ipc-utils";

export interface OfflineRuntimeInfo {
	available: boolean;
	exe?: string;
	models?: { name: string; size?: string }[];
	name?: string;
}

export interface OfflineStatus {
	timestamp: string;
	runtimes: {
		ollama: OfflineRuntimeInfo;
		llamaCpp: OfflineRuntimeInfo;
		lmStudio: OfflineRuntimeInfo;
	};
	localModels: string[];
	offlineReady: boolean;
}

export interface OfflineRoutingEntry {
	provider: string;
	model: string;
}

export interface OfflineRoutingHistoryEntry {
	timestamp: string;
	task: string;
	provider: string;
	model: string;
}

export interface OfflinePolicy {
	version: number;
	airgapStrict: boolean;
	defaultProvider: string;
	routing: Record<string, OfflineRoutingEntry>;
	history: OfflineRoutingHistoryEntry[];
}

export interface OfflineReport {
	total: number;
	providers: Record<string, number>;
	mix: Record<string, number>;
	history: OfflineRoutingHistoryEntry[];
	confidentialityLevel: "local" | "mixed" | "unknown";
}

export interface OfflineModelCatalog {
	cachedAt: string;
	ttlSeconds: number;
	providers: Record<string, string[]>;
	local: {
		ollama: boolean;
		lmStudio: boolean;
		llamaCpp: boolean;
	};
	fromCache: boolean;
	ageSeconds: number;
}

export interface OfflineModeAPI {
	getOfflineStatus: (projectPath: string) => Promise<OfflineStatus>;
	listOfflineModels: (projectPath: string) => Promise<OfflineStatus>;
	scanOfflineModels: (
		projectPath: string,
		force?: boolean,
	) => Promise<OfflineModelCatalog>;
	getOfflinePolicy: (projectPath: string) => Promise<{ policy: OfflinePolicy }>;
	setOfflinePolicy: (
		projectPath: string,
		policy: OfflinePolicy,
	) => Promise<{ policy: OfflinePolicy }>;
	getOfflineReport: (projectPath: string) => Promise<OfflineReport>;
}

export const createOfflineModeAPI = (): OfflineModeAPI => ({
	getOfflineStatus: (projectPath) =>
		invokeIpc("offlineMode:status", { projectPath }),
	listOfflineModels: (projectPath) =>
		invokeIpc("offlineMode:listModels", { projectPath }),
	scanOfflineModels: (projectPath, force) =>
		invokeIpc("offlineMode:scanModels", { projectPath, force }),
	getOfflinePolicy: (projectPath) =>
		invokeIpc("offlineMode:getPolicy", { projectPath }),
	setOfflinePolicy: (projectPath, policy) =>
		invokeIpc("offlineMode:setPolicy", { projectPath, policy }),
	getOfflineReport: (projectPath) =>
		invokeIpc("offlineMode:report", { projectPath }),
});
