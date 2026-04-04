import { create } from "zustand";
import type {
	ContextMeshCompleteResult,
	ContextMeshSummary,
	ContextualRecommendation,
	CrossProjectPattern,
	HandbookEntry,
	ProjectSummary,
	SkillTransfer,
} from "../../shared/types/context-mesh";

export type ContextMeshPhase = "idle" | "analyzing" | "complete" | "error";

// Active tab in the context mesh UI
export type ContextMeshTab =
	| "overview"
	| "patterns"
	| "handbook"
	| "transfers"
	| "recommendations"
	| "projects";

interface ContextMeshState {
	// State
	phase: ContextMeshPhase;
	activeTab: ContextMeshTab;
	status: string;
	streamingOutput: string;
	projects: ProjectSummary[];
	patterns: CrossProjectPattern[];
	handbookEntries: HandbookEntry[];
	skillTransfers: SkillTransfer[];
	recommendations: ContextualRecommendation[];
	summary: ContextMeshSummary | null;
	error: string | null;
	isOpen: boolean;
	isLoading: boolean;

	// Actions
	openDialog: () => void;
	closeDialog: () => void;
	setActiveTab: (tab: ContextMeshTab) => void;
	setPhase: (phase: ContextMeshPhase) => void;
	setStatus: (status: string) => void;
	appendStreamingOutput: (chunk: string) => void;
	setProjects: (projects: ProjectSummary[]) => void;
	setPatterns: (patterns: CrossProjectPattern[]) => void;
	setHandbookEntries: (entries: HandbookEntry[]) => void;
	setSkillTransfers: (transfers: SkillTransfer[]) => void;
	setRecommendations: (recs: ContextualRecommendation[]) => void;
	setSummary: (summary: ContextMeshSummary | null) => void;
	setError: (error: string) => void;
	setIsLoading: (isLoading: boolean) => void;
	removePattern: (patternId: string) => void;
	removeHandbookEntry: (entryId: string) => void;
	updateTransferStatus: (transferId: string, status: string) => void;
	updateRecommendationStatus: (recId: string, status: string) => void;
	reset: () => void;
}

const initialState = {
	phase: "idle" as ContextMeshPhase,
	activeTab: "overview" as ContextMeshTab,
	status: "",
	streamingOutput: "",
	projects: [] as ProjectSummary[],
	patterns: [] as CrossProjectPattern[],
	handbookEntries: [] as HandbookEntry[],
	skillTransfers: [] as SkillTransfer[],
	recommendations: [] as ContextualRecommendation[],
	summary: null as ContextMeshSummary | null,
	error: null as string | null,
	isOpen: false,
	isLoading: false,
};

export const useContextMeshStore = create<ContextMeshState>((set) => ({
	...initialState,

	openDialog: () =>
		set({
			isOpen: true,
			phase: "idle",
			status: "",
			streamingOutput: "",
			error: null,
		}),

	closeDialog: () =>
		set({
			isOpen: false,
			phase: "idle",
			status: "",
			streamingOutput: "",
			error: null,
		}),

	setActiveTab: (tab) => set({ activeTab: tab }),

	setPhase: (phase) => set({ phase }),

	setStatus: (status) => set({ status }),

	appendStreamingOutput: (chunk) =>
		set((state) => ({
			streamingOutput: state.streamingOutput + chunk,
		})),

	setProjects: (projects) => set({ projects }),

	setPatterns: (patterns) => set({ patterns }),

	setHandbookEntries: (entries) => set({ handbookEntries: entries }),

	setSkillTransfers: (transfers) => set({ skillTransfers: transfers }),

	setRecommendations: (recs) => set({ recommendations: recs }),

	setSummary: (summary) => set({ summary }),

	setError: (error) => set({ error, phase: "error" }),

	setIsLoading: (isLoading) => set({ isLoading }),

	removePattern: (patternId) =>
		set((state) => ({
			patterns: state.patterns.filter((p) => p.pattern_id !== patternId),
		})),

	removeHandbookEntry: (entryId) =>
		set((state) => ({
			handbookEntries: state.handbookEntries.filter(
				(e) => e.entry_id !== entryId,
			),
		})),

	updateTransferStatus: (transferId, status) =>
		set((state) => ({
			skillTransfers: state.skillTransfers.map((t) =>
				t.transfer_id === transferId
					? { ...t, status: status as SkillTransfer["status"] }
					: t,
			),
		})),

	updateRecommendationStatus: (recId, status) =>
		set((state) => ({
			recommendations: state.recommendations.map((r) =>
				r.recommendation_id === recId
					? { ...r, status: status as ContextualRecommendation["status"] }
					: r,
			),
		})),

	reset: () => set(initialState),
}));

// ── Async helper functions ──────────────────────────────────────

export async function loadContextMeshProjects(): Promise<void> {
	const store = useContextMeshStore.getState();
	store.setIsLoading(true);
	try {
		const result = await window.electronAPI.invoke("contextMesh:getProjects");
		if (result.success) {
			store.setProjects(result.data);
		}
	} catch (error) {
		console.error("[ContextMesh] Failed to load projects:", error);
	} finally {
		store.setIsLoading(false);
	}
}

export async function loadContextMeshPatterns(): Promise<void> {
	try {
		const result = await window.electronAPI.invoke("contextMesh:getPatterns");
		if (result.success) {
			useContextMeshStore.getState().setPatterns(result.data);
		}
	} catch (error) {
		console.error("[ContextMesh] Failed to load patterns:", error);
	}
}

export async function loadContextMeshHandbook(): Promise<void> {
	try {
		const result = await window.electronAPI.invoke("contextMesh:getHandbook");
		if (result.success) {
			useContextMeshStore.getState().setHandbookEntries(result.data);
		}
	} catch (error) {
		console.error("[ContextMesh] Failed to load handbook:", error);
	}
}

export async function loadContextMeshSkillTransfers(): Promise<void> {
	try {
		const result = await window.electronAPI.invoke(
			"contextMesh:getSkillTransfers",
		);
		if (result.success) {
			useContextMeshStore.getState().setSkillTransfers(result.data);
		}
	} catch (error) {
		console.error("[ContextMesh] Failed to load skill transfers:", error);
	}
}

export async function loadContextMeshRecommendations(
	targetProject?: string,
): Promise<void> {
	try {
		const result = await window.electronAPI.invoke(
			"contextMesh:getRecommendations",
			targetProject,
		);
		if (result.success) {
			useContextMeshStore.getState().setRecommendations(result.data);
		}
	} catch (error) {
		console.error("[ContextMesh] Failed to load recommendations:", error);
	}
}

export async function loadContextMeshSummary(): Promise<void> {
	try {
		const result = await window.electronAPI.invoke("contextMesh:getSummary");
		if (result.success) {
			useContextMeshStore.getState().setSummary(result.data);
		}
	} catch (error) {
		console.error("[ContextMesh] Failed to load summary:", error);
	}
}

export async function registerProject(projectDir: string): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"contextMesh:registerProject",
			projectDir,
		);
		if (result.success) {
			await loadContextMeshProjects();
			await loadContextMeshSummary();
			return true;
		}
		return false;
	} catch (error) {
		console.error("[ContextMesh] Failed to register project:", error);
		return false;
	}
}

export async function unregisterProject(projectDir: string): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"contextMesh:unregisterProject",
			projectDir,
		);
		if (result.success) {
			await loadContextMeshProjects();
			await loadContextMeshSummary();
			return true;
		}
		return false;
	} catch (error) {
		console.error("[ContextMesh] Failed to unregister project:", error);
		return false;
	}
}

export async function deletePattern(patternId: string): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"contextMesh:deletePattern",
			patternId,
		);
		if (result.success) {
			useContextMeshStore.getState().removePattern(patternId);
			return true;
		}
		return false;
	} catch (error) {
		console.error("[ContextMesh] Failed to delete pattern:", error);
		return false;
	}
}

export async function deleteHandbookEntry(entryId: string): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"contextMesh:deleteHandbookEntry",
			entryId,
		);
		if (result.success) {
			useContextMeshStore.getState().removeHandbookEntry(entryId);
			return true;
		}
		return false;
	} catch (error) {
		console.error("[ContextMesh] Failed to delete handbook entry:", error);
		return false;
	}
}

export async function updateSkillTransferStatus(
	transferId: string,
	status: string,
): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"contextMesh:updateTransferStatus",
			transferId,
			status,
		);
		if (result.success) {
			useContextMeshStore.getState().updateTransferStatus(transferId, status);
			return true;
		}
		return false;
	} catch (error) {
		console.error("[ContextMesh] Failed to update transfer status:", error);
		return false;
	}
}

export async function updateRecommendationStatus(
	recId: string,
	status: string,
): Promise<boolean> {
	try {
		const result = await window.electronAPI.invoke(
			"contextMesh:updateRecommendationStatus",
			recId,
			status,
		);
		if (result.success) {
			useContextMeshStore.getState().updateRecommendationStatus(recId, status);
			return true;
		}
		return false;
	} catch (error) {
		console.error(
			"[ContextMesh] Failed to update recommendation status:",
			error,
		);
		return false;
	}
}

export function startContextMeshAnalysis(
	model?: string,
	thinkingLevel?: string,
): void {
	const store = useContextMeshStore.getState();
	store.setPhase("analyzing");
	store.setStatus("Starting analysis...");
	store.appendStreamingOutput("");
	window.electronAPI.send("contextMesh:runAnalysis", model, thinkingLevel);
}

export async function stopContextMeshAnalysis(): Promise<void> {
	await window.electronAPI.invoke("contextMesh:stopAnalysis");
	useContextMeshStore.getState().setPhase("idle");
}

/**
 * Load all context mesh data at once
 */
export async function loadAllContextMeshData(): Promise<void> {
	await Promise.all([
		loadContextMeshProjects(),
		loadContextMeshPatterns(),
		loadContextMeshHandbook(),
		loadContextMeshSkillTransfers(),
		loadContextMeshRecommendations(),
		loadContextMeshSummary(),
	]);
}
