/**
 * Agent Time Travel IPC handlers registration
 *
 * Handles IPC communication between the renderer process and the
 * Time Travel backend API for checkpoint management, fork & re-execute,
 * and decision scoring. Works with any LLM provider.
 */

import type { BrowserWindow } from "electron";
import { ipcMain } from "electron";
import { IPC_CHANNELS } from "../../shared/constants";
import { safeSendToRenderer } from "./utils";

const getBackendUrl = (): string => {
	return process.env.VITE_BACKEND_URL || "http://127.0.0.1:8321";
};

async function timeTravelFetch<T = Record<string, unknown>>(
	path: string,
	options?: RequestInit,
): Promise<T> {
	const url = `${getBackendUrl()}/replay${path}`;
	const res = await fetch(url, {
		headers: { "Content-Type": "application/json" },
		...options,
	});
	if (!res.ok) {
		const err = await res.text();
		throw new Error(err || `HTTP ${res.status}`);
	}
	return res.json() as Promise<T>;
}

/**
 * Register all time-travel-related IPC handlers
 */
export function registerTimeTravelHandlers(
	getMainWindow: () => BrowserWindow | null,
): void {
	// ============================================
	// Checkpoint operations
	// ============================================

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_GENERATE_CHECKPOINTS,
		async (_event, sessionId: string) => {
			try {
				const result = await timeTravelFetch(
					`/sessions/${sessionId}/checkpoints/generate`,
					{
						method: "POST",
					},
				);
				safeSendToRenderer(
					getMainWindow,
					IPC_CHANNELS.TIME_TRAVEL_CHECKPOINTS_READY,
					result,
				);
				return result;
			} catch (error: unknown) {
				const msg = (error as Error).message;
				safeSendToRenderer(getMainWindow, IPC_CHANNELS.TIME_TRAVEL_ERROR, msg);
				return { success: false, error: msg };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_GET_CHECKPOINTS,
		async (_event, sessionId: string) => {
			try {
				return await timeTravelFetch(`/sessions/${sessionId}/checkpoints`);
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_GET_CHECKPOINT,
		async (_event, sessionId: string, checkpointId: string) => {
			try {
				return await timeTravelFetch(
					`/sessions/${sessionId}/checkpoints/${checkpointId}`,
				);
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_ADD_CHECKPOINT,
		async (
			_event,
			sessionId: string,
			stepIndex: number,
			label?: string,
			description?: string,
		) => {
			try {
				return await timeTravelFetch(`/sessions/${sessionId}/checkpoints`, {
					method: "POST",
					body: JSON.stringify({
						step_index: stepIndex,
						label: label || "",
						description: description || "",
					}),
				});
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_DELETE_CHECKPOINT,
		async (_event, sessionId: string, checkpointId: string) => {
			try {
				return await timeTravelFetch(
					`/sessions/${sessionId}/checkpoints/${checkpointId}`,
					{
						method: "DELETE",
					},
				);
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	// ============================================
	// Fork operations
	// ============================================

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_FORK_SESSION,
		async (
			_event,
			sessionId: string,
			forkRequest: {
				checkpoint_id: string;
				modified_prompt?: string;
				additional_instructions?: string;
				fork_provider?: string;
				fork_model?: string;
				fork_api_key?: string;
				fork_base_url?: string;
			},
		) => {
			try {
				const result = await timeTravelFetch(`/sessions/${sessionId}/fork`, {
					method: "POST",
					body: JSON.stringify(forkRequest),
				});
				safeSendToRenderer(
					getMainWindow,
					IPC_CHANNELS.TIME_TRAVEL_FORK_STATUS_CHANGED,
					result,
				);
				return result;
			} catch (error: unknown) {
				const msg = (error as Error).message;
				safeSendToRenderer(getMainWindow, IPC_CHANNELS.TIME_TRAVEL_ERROR, msg);
				return { success: false, error: msg };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_GET_FORK,
		async (_event, forkId: string) => {
			try {
				return await timeTravelFetch(`/forks/${forkId}`);
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_GET_FORK_CONTEXT,
		async (_event, forkId: string) => {
			try {
				return await timeTravelFetch(`/forks/${forkId}/context`);
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_LIST_FORKS,
		async (_event, sessionId?: string) => {
			try {
				const query = sessionId ? `?session_id=${sessionId}` : "";
				return await timeTravelFetch(`/forks${query}`);
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_UPDATE_FORK_STATUS,
		async (_event, forkId: string, status: string) => {
			try {
				return await timeTravelFetch(
					`/forks/${forkId}/status?status=${status}`,
					{
						method: "PATCH",
					},
				);
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_DELETE_FORK,
		async (_event, forkId: string) => {
			try {
				return await timeTravelFetch(`/forks/${forkId}`, { method: "DELETE" });
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	// ============================================
	// Decision scoring operations
	// ============================================

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_SCORE_DECISIONS,
		async (_event, sessionId: string) => {
			try {
				return await timeTravelFetch(`/sessions/${sessionId}/decisions/score`, {
					method: "POST",
				});
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_GET_DECISION_SCORES,
		async (_event, sessionId: string) => {
			try {
				return await timeTravelFetch(`/sessions/${sessionId}/decisions/scores`);
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.TIME_TRAVEL_GET_DECISION_HEATMAP,
		async (_event, sessionId: string) => {
			try {
				return await timeTravelFetch(
					`/sessions/${sessionId}/decisions/heatmap`,
				);
			} catch (error: unknown) {
				return { success: false, error: (error as Error).message };
			}
		},
	);

	console.warn("[IPC] Time Travel handlers registered");
}
