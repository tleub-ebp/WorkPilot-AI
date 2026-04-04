/**
 * AI Pair Programming Preload API (Feature 10)
 *
 * Exposes IPC channels for real parallel coordinated development between
 * the developer and an AI agent working on complementary parts of the codebase.
 */

import { IPC_CHANNELS } from "../../../shared/constants";
import type { IPCResult } from "../../../shared/types";
import {
	createIpcListener,
	type IpcListenerCleanup,
	invokeIpc,
	sendIpc,
} from "./ipc-utils";

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface PairSession {
	id: string;
	projectId: string;
	goal: string;
	devScope: string;
	aiScope: string;
	status: "planning" | "active" | "paused" | "completed" | "error";
	messages: PairMessage[];
	aiActions: AiAction[];
	createdAt: string;
	updatedAt: string;
}

export interface PairMessage {
	id: string;
	role: "user" | "ai";
	content: string;
	timestamp: string;
	isQuestion?: boolean;
}

export interface AiAction {
	id: string;
	actionType:
		| "file_created"
		| "file_modified"
		| "file_deleted"
		| "command_run"
		| "thinking";
	description: string;
	filePath?: string;
	timestamp: string;
	status: "in_progress" | "completed" | "error";
}

export interface PairStreamChunk {
	type:
		| "stream"
		| "status"
		| "action"
		| "question"
		| "conflict"
		| "done"
		| "error";
	content?: string;
	status?: string;
	message?: string;
	actionType?: string;
	filePath?: string;
	description?: string;
	summary?: string;
}

export interface StartSessionParams {
	projectId: string;
	goal: string;
	devScope: string;
	aiScope: string;
}

// ---------------------------------------------------------------------------
// API interface
// ---------------------------------------------------------------------------

export interface PairProgrammingAPI {
	/** Start a new pair programming session */
	startPairSession: (
		params: StartSessionParams,
	) => Promise<IPCResult<PairSession>>;

	/** Stop the active pair programming session */
	stopPairSession: (projectId: string, sessionId: string) => Promise<IPCResult>;

	/** Send a chat message from the developer to the AI */
	sendPairMessage: (
		projectId: string,
		sessionId: string,
		message: string,
	) => void;

	/** Get the current session state */
	getPairSession: (projectId: string) => Promise<IPCResult<PairSession | null>>;

	/** Subscribe to streaming chunks from the AI */
	onPairStreamChunk: (
		callback: (projectId: string, chunk: PairStreamChunk) => void,
	) => IpcListenerCleanup;

	/** Subscribe to session status updates */
	onPairStatus: (
		callback: (projectId: string, status: string, message: string) => void,
	) => IpcListenerCleanup;

	/** Subscribe to AI action events (file created/modified etc.) */
	onPairAiAction: (
		callback: (projectId: string, action: AiAction) => void,
	) => IpcListenerCleanup;

	/** Subscribe to conflict warnings */
	onPairConflict: (
		callback: (projectId: string, filePath: string, message: string) => void,
	) => IpcListenerCleanup;

	/** Subscribe to error events */
	onPairError: (
		callback: (projectId: string, error: string) => void,
	) => IpcListenerCleanup;

	/** Subscribe to session completion */
	onPairComplete: (
		callback: (projectId: string, summary: string) => void,
	) => IpcListenerCleanup;
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

export function createPairProgrammingAPI(): PairProgrammingAPI {
	return {
		startPairSession: (params) =>
			invokeIpc<IPCResult<PairSession>>(
				IPC_CHANNELS.PAIR_PROGRAMMING_START,
				params,
			),

		stopPairSession: (projectId, sessionId) =>
			invokeIpc<IPCResult>(
				IPC_CHANNELS.PAIR_PROGRAMMING_STOP,
				projectId,
				sessionId,
			),

		sendPairMessage: (projectId, sessionId, message) =>
			sendIpc(
				IPC_CHANNELS.PAIR_PROGRAMMING_SEND_MESSAGE,
				projectId,
				sessionId,
				message,
			),

		getPairSession: (projectId) =>
			invokeIpc<IPCResult<PairSession | null>>(
				IPC_CHANNELS.PAIR_PROGRAMMING_GET_SESSION,
				projectId,
			),

		onPairStreamChunk: (callback) =>
			createIpcListener<[string, PairStreamChunk]>(
				IPC_CHANNELS.PAIR_PROGRAMMING_STREAM_CHUNK,
				callback,
			),

		onPairStatus: (callback) =>
			createIpcListener<[string, string, string]>(
				IPC_CHANNELS.PAIR_PROGRAMMING_STATUS,
				callback,
			),

		onPairAiAction: (callback) =>
			createIpcListener<[string, AiAction]>(
				IPC_CHANNELS.PAIR_PROGRAMMING_AI_ACTION,
				callback,
			),

		onPairConflict: (callback) =>
			createIpcListener<[string, string, string]>(
				IPC_CHANNELS.PAIR_PROGRAMMING_CONFLICT,
				callback,
			),

		onPairError: (callback) =>
			createIpcListener<[string, string]>(
				IPC_CHANNELS.PAIR_PROGRAMMING_ERROR,
				callback,
			),

		onPairComplete: (callback) =>
			createIpcListener<[string, string]>(
				IPC_CHANNELS.PAIR_PROGRAMMING_COMPLETE,
				callback,
			),
	};
}
