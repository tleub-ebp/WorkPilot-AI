/**
 * Arena Mode preload API module
 */

import type {
	ArenaAnalytics,
	ArenaBattle,
	ArenaBattleCompleteEvent,
	ArenaBattleProgressEvent,
	ArenaBattleResultEvent,
	ArenaLabel,
	ArenaTaskType,
} from "../../../shared/types/arena";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface ArenaStartBattleRequest {
	taskType: ArenaTaskType;
	prompt: string;
	profileIds: string[];
	projectPath?: string;
}

export interface ArenaVoteRequest {
	battleId: string;
	winnerLabel: ArenaLabel;
	winnerProfileId: string;
	taskType: ArenaTaskType;
	votedAt: number;
}

export interface ArenaAPI {
	arenaStartBattle: (
		request: ArenaStartBattleRequest,
	) => Promise<{ success: boolean; data?: ArenaBattle; error?: string }>;
	arenaVote: (
		vote: ArenaVoteRequest,
	) => Promise<{ success: boolean; error?: string }>;
	arenaGetBattles: () => Promise<{
		success: boolean;
		data?: ArenaBattle[];
		error?: string;
	}>;
	arenaGetAnalytics: () => Promise<{
		success: boolean;
		data?: ArenaAnalytics;
		error?: string;
	}>;
	arenaClearHistory: () => Promise<{ success: boolean; error?: string }>;
	arenaGetProfiles: () => Promise<{
		success: boolean;
		data?: unknown[];
		error?: string;
	}>;

	onArenaBattleProgress: (
		callback: (event: ArenaBattleProgressEvent) => void,
	) => () => void;
	onArenaBattleResult: (
		callback: (event: ArenaBattleResultEvent) => void,
	) => () => void;
	onArenaBattleComplete: (
		callback: (event: ArenaBattleCompleteEvent) => void,
	) => () => void;
	onArenaBattleError: (
		callback: (event: { battleId: string; error: string }) => void,
	) => () => void;
}

export function createArenaAPI(): ArenaAPI {
	return {
		arenaStartBattle: (request) => invokeIpc("arena:startBattle", request),
		arenaVote: (vote) => invokeIpc("arena:vote", vote),
		arenaGetBattles: () => invokeIpc("arena:getBattles"),
		arenaGetAnalytics: () => invokeIpc("arena:getAnalytics"),
		arenaClearHistory: () => invokeIpc("arena:clearHistory"),
		arenaGetProfiles: () => invokeIpc("arena:getProfiles"),

		onArenaBattleProgress: (callback) =>
			createIpcListener("arena:battleProgress", callback),
		onArenaBattleResult: (callback) =>
			createIpcListener("arena:battleResult", callback),
		onArenaBattleComplete: (callback) =>
			createIpcListener("arena:battleComplete", callback),
		onArenaBattleError: (callback) =>
			createIpcListener("arena:battleError", callback),
	};
}
