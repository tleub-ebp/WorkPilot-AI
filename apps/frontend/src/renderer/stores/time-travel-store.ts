/**
 * Agent Time Travel Store — Zustand state management.
 *
 * Manages:
 * - Checkpoint generation and browsing
 * - Fork creation and management (any LLM provider)
 * - Decision scoring and heatmap
 * - A/B comparison between original and forked sessions
 */

import type {
	Checkpoint,
	DecisionHeatmap,
	DecisionScore,
	ForkContext,
	ForkSession,
} from "@shared/types/time-travel";
import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TimeTravelState {
	// Checkpoints
	checkpoints: Checkpoint[];
	checkpointsLoading: boolean;
	selectedCheckpoint: Checkpoint | null;

	// Forks
	forks: ForkSession[];
	forksLoading: boolean;
	selectedFork: ForkSession | null;
	forkContext: ForkContext | null;

	// Decision scoring
	decisionScores: DecisionScore[];
	decisionScoresLoading: boolean;
	decisionHeatmap: DecisionHeatmap | null;
	decisionHeatmapLoading: boolean;

	// Fork form state
	forkFormVisible: boolean;
	forkFormCheckpointId: string | null;

	// Error
	error: string | null;

	// Checkpoint actions
	generateCheckpoints: (sessionId: string) => Promise<void>;
	fetchCheckpoints: (sessionId: string) => Promise<void>;
	addManualCheckpoint: (
		sessionId: string,
		stepIndex: number,
		label?: string,
		description?: string,
	) => Promise<void>;
	deleteCheckpoint: (sessionId: string, checkpointId: string) => Promise<void>;
	selectCheckpoint: (checkpoint: Checkpoint | null) => void;

	// Fork actions
	forkSession: (
		sessionId: string,
		checkpointId: string,
		options: {
			modifiedPrompt?: string;
			additionalInstructions?: string;
			forkProvider?: string;
			forkModel?: string;
			forkApiKey?: string;
			forkBaseUrl?: string;
		},
	) => Promise<ForkSession | null>;
	fetchForks: (sessionId?: string) => Promise<void>;
	fetchForkContext: (forkId: string) => Promise<void>;
	deleteFork: (forkId: string) => Promise<void>;
	selectFork: (fork: ForkSession | null) => void;

	// Fork form
	openForkForm: (checkpointId: string) => void;
	closeForkForm: () => void;

	// Decision scoring actions
	scoreDecisions: (sessionId: string) => Promise<void>;
	fetchDecisionScores: (sessionId: string) => Promise<void>;
	fetchDecisionHeatmap: (sessionId: string) => Promise<void>;

	// Cleanup
	reset: () => void;
}

// ---------------------------------------------------------------------------
// IPC helper
// ---------------------------------------------------------------------------

const ipc = (
	window as unknown as {
		electronAPI: Record<
			string,
			(...args: unknown[]) => Promise<Record<string, unknown>>
		>;
	}
).electronAPI;

async function ipcInvoke<T = Record<string, unknown>>(
	channel: string,
	...args: unknown[]
): Promise<T> {
	if (ipc?.invoke) {
		return (
			ipc as unknown as {
				invoke: (channel: string, ...args: unknown[]) => Promise<T>;
			}
		).invoke(channel, ...args);
	}
	// Fallback: direct window.electronAPI call pattern
	const fn = (
		window as unknown as Record<
			string,
			Record<string, (...args: unknown[]) => Promise<T>>
		>
	).electronAPI;
	if (fn) {
		// Try the IPC channel directly — electronAPI exposes handlers by channel name
		const handler = (
			fn as unknown as Record<string, (...args: unknown[]) => Promise<T>>
		)[channel];
		if (typeof handler === "function") {
			return handler(...args);
		}
	}
	throw new Error(`IPC channel not available: ${channel}`);
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

const initialState = {
	checkpoints: [] as Checkpoint[],
	checkpointsLoading: false,
	selectedCheckpoint: null as Checkpoint | null,
	forks: [] as ForkSession[],
	forksLoading: false,
	selectedFork: null as ForkSession | null,
	forkContext: null as ForkContext | null,
	decisionScores: [] as DecisionScore[],
	decisionScoresLoading: false,
	decisionHeatmap: null as DecisionHeatmap | null,
	decisionHeatmapLoading: false,
	forkFormVisible: false,
	forkFormCheckpointId: null as string | null,
	error: null as string | null,
};

export const useTimeTravelStore = create<TimeTravelState>((set) => ({
	...initialState,

	// --- Checkpoints ---

	generateCheckpoints: async (sessionId: string) => {
		set({ checkpointsLoading: true, error: null });
		try {
			const res = await ipcInvoke<{
				success: boolean;
				checkpoints: Checkpoint[];
				error?: string;
			}>("timeTravel:generateCheckpoints", sessionId);
			if (res.success) {
				set({ checkpoints: res.checkpoints || [], checkpointsLoading: false });
			} else {
				set({
					error: res.error || "Failed to generate checkpoints",
					checkpointsLoading: false,
				});
			}
		} catch (e) {
			set({ error: (e as Error).message, checkpointsLoading: false });
		}
	},

	fetchCheckpoints: async (sessionId: string) => {
		set({ checkpointsLoading: true, error: null });
		try {
			const res = await ipcInvoke<{
				success: boolean;
				checkpoints: Checkpoint[];
				error?: string;
			}>("timeTravel:getCheckpoints", sessionId);
			if (res.success) {
				set({ checkpoints: res.checkpoints || [], checkpointsLoading: false });
			} else {
				set({ checkpoints: [], checkpointsLoading: false });
			}
		} catch (e) {
			set({ error: (e as Error).message, checkpointsLoading: false });
		}
	},

	addManualCheckpoint: async (
		sessionId: string,
		stepIndex: number,
		label?: string,
		description?: string,
	) => {
		try {
			const res = await ipcInvoke<{
				success: boolean;
				checkpoint: Checkpoint;
				error?: string;
			}>("timeTravel:addCheckpoint", sessionId, stepIndex, label, description);
			if (res.success && res.checkpoint) {
				set((s) => ({
					checkpoints: [...s.checkpoints, res.checkpoint].sort(
						(a, b) => a.step_index - b.step_index,
					),
				}));
			}
		} catch (e) {
			set({ error: (e as Error).message });
		}
	},

	deleteCheckpoint: async (sessionId: string, checkpointId: string) => {
		try {
			await ipcInvoke("timeTravel:deleteCheckpoint", sessionId, checkpointId);
			set((s) => ({
				checkpoints: s.checkpoints.filter((cp) => cp.id !== checkpointId),
				selectedCheckpoint:
					s.selectedCheckpoint?.id === checkpointId
						? null
						: s.selectedCheckpoint,
			}));
		} catch (e) {
			set({ error: (e as Error).message });
		}
	},

	selectCheckpoint: (checkpoint) => {
		set({ selectedCheckpoint: checkpoint });
	},

	// --- Forks ---

	forkSession: async (sessionId, checkpointId, options) => {
		try {
			const res = await ipcInvoke<{
				success: boolean;
				fork: ForkSession;
				error?: string;
			}>("timeTravel:forkSession", sessionId, {
				checkpoint_id: checkpointId,
				modified_prompt: options.modifiedPrompt || "",
				additional_instructions: options.additionalInstructions || "",
				fork_provider: options.forkProvider || "",
				fork_model: options.forkModel || "",
				fork_api_key: options.forkApiKey || "",
				fork_base_url: options.forkBaseUrl || "",
			});
			if (res.success && res.fork) {
				set((s) => ({
					forks: [res.fork, ...s.forks],
					forkFormVisible: false,
					forkFormCheckpointId: null,
				}));
				return res.fork;
			}
			set({ error: res.error || "Failed to create fork" });
			return null;
		} catch (e) {
			set({ error: (e as Error).message });
			return null;
		}
	},

	fetchForks: async (sessionId?: string) => {
		set({ forksLoading: true, error: null });
		try {
			const res = await ipcInvoke<{
				success: boolean;
				forks: ForkSession[];
				error?: string;
			}>("timeTravel:listForks", sessionId);
			if (res.success) {
				set({ forks: res.forks || [], forksLoading: false });
			} else {
				set({ forks: [], forksLoading: false });
			}
		} catch (e) {
			set({ error: (e as Error).message, forksLoading: false });
		}
	},

	fetchForkContext: async (forkId: string) => {
		try {
			const res = await ipcInvoke<{
				success: boolean;
				context: ForkContext;
				error?: string;
			}>("timeTravel:getForkContext", forkId);
			if (res.success) {
				set({ forkContext: res.context });
			}
		} catch (e) {
			set({ error: (e as Error).message });
		}
	},

	deleteFork: async (forkId: string) => {
		try {
			await ipcInvoke("timeTravel:deleteFork", forkId);
			set((s) => ({
				forks: s.forks.filter((f) => f.fork_id !== forkId),
				selectedFork:
					s.selectedFork?.fork_id === forkId ? null : s.selectedFork,
				forkContext: s.forkContext?.fork_id === forkId ? null : s.forkContext,
			}));
		} catch (e) {
			set({ error: (e as Error).message });
		}
	},

	selectFork: (fork) => {
		set({ selectedFork: fork, forkContext: null });
	},

	// --- Fork form ---

	openForkForm: (checkpointId: string) => {
		set({ forkFormVisible: true, forkFormCheckpointId: checkpointId });
	},

	closeForkForm: () => {
		set({ forkFormVisible: false, forkFormCheckpointId: null });
	},

	// --- Decision scoring ---

	scoreDecisions: async (sessionId: string) => {
		set({ decisionScoresLoading: true, error: null });
		try {
			const res = await ipcInvoke<{
				success: boolean;
				scores: DecisionScore[];
				error?: string;
			}>("timeTravel:scoreDecisions", sessionId);
			if (res.success) {
				set({ decisionScores: res.scores || [], decisionScoresLoading: false });
			} else {
				set({
					error: res.error || "Failed to score decisions",
					decisionScoresLoading: false,
				});
			}
		} catch (e) {
			set({ error: (e as Error).message, decisionScoresLoading: false });
		}
	},

	fetchDecisionScores: async (sessionId: string) => {
		set({ decisionScoresLoading: true, error: null });
		try {
			const res = await ipcInvoke<{
				success: boolean;
				scores: DecisionScore[];
				error?: string;
			}>("timeTravel:getDecisionScores", sessionId);
			if (res.success) {
				set({ decisionScores: res.scores || [], decisionScoresLoading: false });
			} else {
				set({ decisionScores: [], decisionScoresLoading: false });
			}
		} catch (e) {
			set({ error: (e as Error).message, decisionScoresLoading: false });
		}
	},

	fetchDecisionHeatmap: async (sessionId: string) => {
		set({ decisionHeatmapLoading: true, error: null });
		try {
			const res = await ipcInvoke<{
				success: boolean;
				heatmap: DecisionHeatmap;
				error?: string;
			}>("timeTravel:getDecisionHeatmap", sessionId);
			if (res.success) {
				set({ decisionHeatmap: res.heatmap, decisionHeatmapLoading: false });
			} else {
				set({ decisionHeatmap: null, decisionHeatmapLoading: false });
			}
		} catch (e) {
			set({ error: (e as Error).message, decisionHeatmapLoading: false });
		}
	},

	// --- Cleanup ---

	reset: () => {
		set(initialState);
	},
}));
