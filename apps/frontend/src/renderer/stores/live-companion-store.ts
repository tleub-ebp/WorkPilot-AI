import { create } from "zustand";
import type {
	CompanionConfig,
	CompanionState,
	FileChangeEvent,
	LiveSuggestion,
	TakeoverProposal,
} from "../../shared/types/live-companion";

interface LiveCompanionStoreState {
	// State
	companionState: CompanionState;
	config: CompanionConfig | null;
	suggestions: LiveSuggestion[];
	takeovers: TakeoverProposal[];
	recentChanges: FileChangeEvent[];
	error: string | null;
	isLoading: boolean;

	// Actions
	setCompanionState: (state: CompanionState) => void;
	setConfig: (config: CompanionConfig) => void;
	setSuggestions: (suggestions: LiveSuggestion[]) => void;
	addSuggestion: (suggestion: LiveSuggestion) => void;
	removeSuggestion: (suggestionId: string) => void;
	setTakeovers: (takeovers: TakeoverProposal[]) => void;
	addTakeover: (proposal: TakeoverProposal) => void;
	removeTakeover: (proposalId: string) => void;
	addFileChange: (event: FileChangeEvent) => void;
	setError: (error: string | null) => void;
	setIsLoading: (isLoading: boolean) => void;
	reset: () => void;
}

const initialCompanionState: CompanionState = {
	active: false,
	watching_project: "",
	files_watched: 0,
	changes_detected: 0,
	suggestions_generated: 0,
	suggestions_accepted: 0,
	takeovers_proposed: 0,
	takeovers_accepted: 0,
	started_at: "",
	last_change_at: "",
};

const initialState = {
	companionState: initialCompanionState,
	config: null as CompanionConfig | null,
	suggestions: [] as LiveSuggestion[],
	takeovers: [] as TakeoverProposal[],
	recentChanges: [] as FileChangeEvent[],
	error: null as string | null,
	isLoading: false,
};

export const useLiveCompanionStore = create<LiveCompanionStoreState>((set) => ({
	...initialState,

	setCompanionState: (companionState) => set({ companionState }),

	setConfig: (config) => set({ config }),

	setSuggestions: (suggestions) => set({ suggestions }),

	addSuggestion: (suggestion) =>
		set((state) => ({
			suggestions: [suggestion, ...state.suggestions].slice(0, 50),
		})),

	removeSuggestion: (suggestionId) =>
		set((state) => ({
			suggestions: state.suggestions.filter(
				(s) => s.suggestion_id !== suggestionId,
			),
		})),

	setTakeovers: (takeovers) => set({ takeovers }),

	addTakeover: (proposal) =>
		set((state) => ({
			takeovers: [proposal, ...state.takeovers],
		})),

	removeTakeover: (proposalId) =>
		set((state) => ({
			takeovers: state.takeovers.filter((t) => t.proposal_id !== proposalId),
		})),

	addFileChange: (event) =>
		set((state) => ({
			recentChanges: [event, ...state.recentChanges].slice(0, 30),
		})),

	setError: (error) => set({ error }),

	setIsLoading: (isLoading) => set({ isLoading }),

	reset: () => set(initialState),
}));

// ── Async helper functions ──────────────────────────────────────

export async function startCompanion(projectDir: string): Promise<boolean> {
	const store = useLiveCompanionStore.getState();
	store.setIsLoading(true);
	try {
		const result = await window.electronAPI.invoke(
			"liveCompanion:start",
			projectDir,
		);
		return result.success;
	} catch (error) {
		console.error("[LiveCompanion] Failed to start:", error);
		return false;
	} finally {
		store.setIsLoading(false);
	}
}

export async function stopCompanion(): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke("liveCompanion:stop");
		return result.success;
	} catch (error) {
		console.error("[LiveCompanion] Failed to stop:", error);
		return false;
	}
}

export async function loadCompanionState(): Promise<void> {
	try {
		const result = await window.electronAPI.invoke("liveCompanion:getState");
		if (result.success) {
			useLiveCompanionStore.getState().setCompanionState(result.data);
		}
	} catch (error) {
		console.error("[LiveCompanion] Failed to load state:", error);
	}
}

export async function loadCompanionConfig(): Promise<void> {
	try {
		const result = await window.electronAPI.invoke("liveCompanion:getConfig");
		if (result.success) {
			useLiveCompanionStore.getState().setConfig(result.data);
		}
	} catch (error) {
		console.error("[LiveCompanion] Failed to load config:", error);
	}
}

export async function updateCompanionConfig(
	updates: Partial<CompanionConfig>,
): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"liveCompanion:updateConfig",
			updates,
		);
		if (result.success) {
			useLiveCompanionStore.getState().setConfig(result.data);
			return true;
		}
		return false;
	} catch (error) {
		console.error("[LiveCompanion] Failed to update config:", error);
		return false;
	}
}

export async function loadSuggestions(): Promise<void> {
	try {
		const result = await window.electronAPI.invoke(
			"liveCompanion:getSuggestions",
		);
		if (result.success) {
			useLiveCompanionStore.getState().setSuggestions(result.data);
		}
	} catch (error) {
		console.error("[LiveCompanion] Failed to load suggestions:", error);
	}
}

export async function dismissSuggestion(
	suggestionId: string,
): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"liveCompanion:dismissSuggestion",
			suggestionId,
		);
		if (result.success) {
			useLiveCompanionStore.getState().removeSuggestion(suggestionId);
			return true;
		}
		return false;
	} catch (error) {
		console.error("[LiveCompanion] Failed to dismiss suggestion:", error);
		return false;
	}
}

export async function applySuggestion(suggestionId: string): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"liveCompanion:applySuggestion",
			suggestionId,
		);
		if (result.success) {
			useLiveCompanionStore.getState().removeSuggestion(suggestionId);
			return true;
		}
		return false;
	} catch (error) {
		console.error("[LiveCompanion] Failed to apply suggestion:", error);
		return false;
	}
}

export async function loadTakeovers(): Promise<void> {
	try {
		const result = await window.electronAPI.invoke(
			"liveCompanion:getTakeovers",
		);
		if (result.success) {
			useLiveCompanionStore.getState().setTakeovers(result.data);
		}
	} catch (error) {
		console.error("[LiveCompanion] Failed to load takeovers:", error);
	}
}

export async function acceptTakeover(proposalId: string): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"liveCompanion:acceptTakeover",
			proposalId,
		);
		if (result.success) {
			useLiveCompanionStore.getState().removeTakeover(proposalId);
			return true;
		}
		return false;
	} catch (error) {
		console.error("[LiveCompanion] Failed to accept takeover:", error);
		return false;
	}
}

export async function declineTakeover(proposalId: string): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"liveCompanion:declineTakeover",
			proposalId,
		);
		if (result.success) {
			useLiveCompanionStore.getState().removeTakeover(proposalId);
			return true;
		}
		return false;
	} catch (error) {
		console.error("[LiveCompanion] Failed to decline takeover:", error);
		return false;
	}
}
