import { create } from "zustand";
import type { DecisionEntry } from "../../shared/types/decision-logger";

// Max live entries kept in memory per task (prevents unbounded growth)
const MAX_LIVE_ENTRIES = 500;

interface DecisionLoggerState {
	// Live entries keyed by taskId
	entriesByTask: Record<string, DecisionEntry[]>;
	// Currently viewed taskId
	activeTaskId: string | null;
	// Loading state for historical log fetch
	isLoadingHistory: boolean;

	// Actions
	setActiveTask: (taskId: string | null) => void;
	addLiveEntry: (taskId: string, entry: DecisionEntry) => void;
	setHistoricalEntries: (taskId: string, entries: DecisionEntry[]) => void;
	clearEntries: (taskId: string) => void;
	setLoadingHistory: (loading: boolean) => void;
}

export const useDecisionLoggerStore = create<DecisionLoggerState>(
	(set, _get) => ({
		entriesByTask: {},
		activeTaskId: null,
		isLoadingHistory: false,

		setActiveTask: (taskId) => set({ activeTaskId: taskId }),

		addLiveEntry: (taskId, entry) =>
			set((state) => {
				const existing = state.entriesByTask[taskId] ?? [];
				// Avoid duplicates by id
				if (
					existing.some(
						(e) => e.id === entry.id && e.session_id === entry.session_id,
					)
				) {
					return state;
				}
				const updated = [...existing, entry];
				return {
					entriesByTask: {
						...state.entriesByTask,
						[taskId]:
							updated.length > MAX_LIVE_ENTRIES
								? updated.slice(-MAX_LIVE_ENTRIES)
								: updated,
					},
				};
			}),

		setHistoricalEntries: (taskId, entries) =>
			set((state) => {
				// Merge historical entries with any live entries not already present
				const live = state.entriesByTask[taskId] ?? [];
				const historicalIds = new Set(
					entries.map((e) => `${e.session_id}:${e.id}`),
				);
				const liveOnly = live.filter(
					(e) => !historicalIds.has(`${e.session_id}:${e.id}`),
				);
				const merged = [...entries, ...liveOnly].sort((a, b) =>
					a.timestamp.localeCompare(b.timestamp),
				);
				return {
					entriesByTask: {
						...state.entriesByTask,
						[taskId]: merged,
					},
				};
			}),

		clearEntries: (taskId) =>
			set((state) => ({
				entriesByTask: { ...state.entriesByTask, [taskId]: [] },
			})),

		setLoadingHistory: (loading) => set({ isLoadingHistory: loading }),
	}),
);

// ── Selectors ───────────────────────────────────────────────────────────────

export function selectEntriesForTask(
	state: DecisionLoggerState,
	taskId: string,
): DecisionEntry[] {
	return state.entriesByTask[taskId] ?? [];
}
