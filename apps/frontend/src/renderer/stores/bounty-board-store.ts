/**
 * Bounty Board Store — competitive multi-agent rounds.
 *
 * Holds the current bounty result, archived rounds for the active spec,
 * and user-configured contestant slots (provider/model/profile).
 */

import { create } from "zustand";
import type {
	BountyContestantInput,
	BountyResult,
} from "../../preload/api/modules/bounty-board-api";

interface BountyBoardState {
	contestants: BountyContestantInput[];
	current: BountyResult | null;
	archives: BountyResult[];
	loading: boolean;
	error: string | null;

	addContestant: (c: BountyContestantInput) => void;
	updateContestant: (index: number, patch: Partial<BountyContestantInput>) => void;
	removeContestant: (index: number) => void;
	resetContestants: () => void;

	startBounty: (projectPath: string, specId: string) => Promise<void>;
	loadArchives: (projectPath: string, specId: string) => Promise<void>;
	clear: () => void;
}

const DEFAULT_CONTESTANTS: BountyContestantInput[] = [
	{ provider: "anthropic", model: "claude-sonnet-4-6" },
	{ provider: "openai", model: "gpt-4o" },
	{ provider: "google", model: "gemini-2.5-pro" },
];

export const useBountyBoardStore = create<BountyBoardState>((set, get) => ({
	contestants: DEFAULT_CONTESTANTS,
	current: null,
	archives: [],
	loading: false,
	error: null,

	addContestant: (c) =>
		set((state) => ({ contestants: [...state.contestants, c] })),

	updateContestant: (index, patch) =>
		set((state) => ({
			contestants: state.contestants.map((c, i) =>
				i === index ? { ...c, ...patch } : c,
			),
		})),

	removeContestant: (index) =>
		set((state) => ({
			contestants: state.contestants.filter((_, i) => i !== index),
		})),

	resetContestants: () => set({ contestants: DEFAULT_CONTESTANTS }),

	startBounty: async (projectPath, specId) => {
		const api = globalThis.electronAPI;
		if (!api?.startBounty) {
			set({ error: "Bounty Board API unavailable" });
			return;
		}
		set({ loading: true, error: null });
		try {
			const { result } = await api.startBounty({
				projectPath,
				specId,
				contestants: get().contestants,
			});
			set({ current: result, loading: false });
			await get().loadArchives(projectPath, specId);
		} catch (e) {
			set({ error: String(e), loading: false });
		}
	},

	loadArchives: async (projectPath, specId) => {
		const api = globalThis.electronAPI;
		if (!api?.listBountyArchives) return;
		try {
			const { archives } = await api.listBountyArchives({
				projectPath,
				specId,
			});
			set({ archives });
		} catch (e) {
			set({ error: String(e) });
		}
	},

	clear: () => set({ current: null, error: null }),
}));
