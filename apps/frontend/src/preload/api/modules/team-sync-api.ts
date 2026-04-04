/**
 * Team Knowledge Sync Preload API (Feature 31)
 */

import { IPC_CHANNELS } from "../../../shared/constants/ipc";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface TeamSyncStatus {
	enabled: boolean;
	mode: "directory" | "http";
	team_id: string;
	member_id: string;
	sync_path: string;
	server_url: string;
	peers: string[];
	last_export: string | null;
	local_episode_count: number;
	imported_episode_count: number;
	server_running: boolean;
	server_port: number;
}

export interface TeamSyncPeer {
	member_id: string;
	exported_at: string | null;
	episode_count: number;
	project: string;
	is_self: boolean;
}

export interface TeamSyncEpisode {
	type: string;
	content: string;
	spec: string;
	timestamp: string;
	member_id: string;
	tags: string[];
	metadata: Record<string, unknown>;
}

export interface TeamSyncConfig {
	mode?: "directory" | "http";
	sync_path?: string;
	team_id?: string;
	member_id?: string;
	server_url?: string;
	server_host?: string;
	server_port?: number;
	auto_sync_interval?: number;
	auto_push?: boolean;
}

export interface TeamSyncAPI {
	teamSyncGetStatus: (
		projectDir: string,
	) => Promise<{ success: boolean; data?: TeamSyncStatus; error?: string }>;
	teamSyncPush: (
		projectDir: string,
	) => Promise<{ success: boolean; data?: unknown; error?: string }>;
	teamSyncPull: (
		projectDir: string,
	) => Promise<{ success: boolean; data?: unknown; error?: string }>;
	teamSyncListPeers: (
		projectDir: string,
	) => Promise<{ success: boolean; data?: TeamSyncPeer[]; error?: string }>;
	teamSyncGetPeerEpisodes: (
		projectDir: string,
		memberId: string,
	) => Promise<{ success: boolean; data?: TeamSyncEpisode[]; error?: string }>;
	teamSyncConfigure: (
		projectDir: string,
		config: TeamSyncConfig,
	) => Promise<{ success: boolean; error?: string }>;
	teamSyncStartServer: (
		projectDir: string,
		port?: number,
	) => Promise<{ success: boolean; port?: number; error?: string }>;
	teamSyncStopServer: () => Promise<{ success: boolean }>;
	onTeamSyncServerStatus: (
		callback: (status: { running: boolean; port: number }) => void,
	) => () => void;
	onTeamSyncProgress: (
		callback: (progress: { step: string; message: string }) => void,
	) => () => void;
}

export function createTeamSyncAPI(): TeamSyncAPI {
	return {
		teamSyncGetStatus: (projectDir) =>
			invokeIpc(IPC_CHANNELS.TEAM_SYNC_GET_STATUS, projectDir),

		teamSyncPush: (projectDir) =>
			invokeIpc(IPC_CHANNELS.TEAM_SYNC_PUSH, projectDir),

		teamSyncPull: (projectDir) =>
			invokeIpc(IPC_CHANNELS.TEAM_SYNC_PULL, projectDir),

		teamSyncListPeers: (projectDir) =>
			invokeIpc(IPC_CHANNELS.TEAM_SYNC_LIST_PEERS, projectDir),

		teamSyncGetPeerEpisodes: (projectDir, memberId) =>
			invokeIpc(IPC_CHANNELS.TEAM_SYNC_GET_PEER_EPISODES, projectDir, memberId),

		teamSyncConfigure: (projectDir, config) =>
			invokeIpc(IPC_CHANNELS.TEAM_SYNC_CONFIGURE, projectDir, config),

		teamSyncStartServer: (projectDir, port) =>
			invokeIpc(IPC_CHANNELS.TEAM_SYNC_START_SERVER, projectDir, port),

		teamSyncStopServer: () => invokeIpc(IPC_CHANNELS.TEAM_SYNC_STOP_SERVER),

		onTeamSyncServerStatus: (callback) =>
			createIpcListener<[{ running: boolean; port: number }]>(
				IPC_CHANNELS.TEAM_SYNC_SERVER_STATUS,
				callback,
			),

		onTeamSyncProgress: (callback) =>
			createIpcListener<[{ step: string; message: string }]>(
				IPC_CHANNELS.TEAM_SYNC_SYNC_PROGRESS,
				callback,
			),
	};
}
