import { create } from "zustand";
import type {
	SpecRefinementEvent,
	SpecRefinementResult,
} from "../../preload/api/modules/spec-refinement-api";
import type { RefinementHistory } from "../../shared/types/spec-refinement";

export type SpecRefinementPhase = "idle" | "scanning" | "complete" | "error";

interface SpecRefinementState {
	phase: SpecRefinementPhase;
	status: string;
	histories: RefinementHistory[];
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setResult: (result: SpecRefinementResult) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useSpecRefinementStore = create<SpecRefinementState>((set) => ({
	phase: "idle",
	status: "",
	histories: [],
	error: null,

	startScan: async (projectPath) => {
		if (!projectPath) {
			set({ phase: "error", error: "No project selected" });
			return;
		}
		set({
			phase: "scanning",
			status: "Starting scan...",
			histories: [],
			error: null,
		});
		try {
			const result = await globalThis.electronAPI.runSpecRefinementScan({
				projectPath,
			});
			set({ phase: "complete", histories: result.histories, status: "" });
		} catch (err) {
			set({
				phase: "error",
				error: err instanceof Error ? err.message : String(err),
			});
		}
	},

	cancelScan: async () => {
		await globalThis.electronAPI.cancelSpecRefinementScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setResult: (result) =>
		set({ histories: result.histories, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", histories: [], error: null }),
}));

export function setupSpecRefinementListeners(): () => void {
	const store = () => useSpecRefinementStore.getState();

	const unsubEvent = globalThis.electronAPI.onSpecRefinementEvent(
		(event: SpecRefinementEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onSpecRefinementResult(
		(result: SpecRefinementResult) => {
			store().setResult(result);
		},
	);

	const unsubError = globalThis.electronAPI.onSpecRefinementError(
		(error: string) => {
			store().setError(error);
		},
	);

	return () => {
		unsubEvent();
		unsubResult();
		unsubError();
	};
}
