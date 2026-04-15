import { create } from "zustand";
import type { ParsedNotebook } from "../../shared/types/notebook-agent";
import type {
	NotebookAgentEvent,
	NotebookAgentResult,
} from "../../preload/api/modules/notebook-agent-api";

export type NotebookAgentPhase = "idle" | "scanning" | "complete" | "error";

interface NotebookAgentState {
	phase: NotebookAgentPhase;
	status: string;
	notebooks: ParsedNotebook[];
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setResult: (result: NotebookAgentResult) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useNotebookAgentStore = create<NotebookAgentState>((set) => ({
	phase: "idle",
	status: "",
	notebooks: [],
	error: null,

	startScan: async (projectPath) => {
		if (!projectPath) {
			set({ phase: "error", error: "No project selected" });
			return;
		}
		set({
			phase: "scanning",
			status: "Starting scan...",
			notebooks: [],
			error: null,
		});
		try {
			const result = await globalThis.electronAPI.runNotebookAgentScan({
				projectPath,
			});
			set({ phase: "complete", notebooks: result.notebooks, status: "" });
		} catch (err) {
			set({
				phase: "error",
				error: err instanceof Error ? err.message : String(err),
			});
		}
	},

	cancelScan: async () => {
		await globalThis.electronAPI.cancelNotebookAgentScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setResult: (result) =>
		set({ notebooks: result.notebooks, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", notebooks: [], error: null }),
}));

export function setupNotebookAgentListeners(): () => void {
	const store = () => useNotebookAgentStore.getState();

	const unsubEvent = globalThis.electronAPI.onNotebookAgentEvent(
		(event: NotebookAgentEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onNotebookAgentResult(
		(result: NotebookAgentResult) => {
			store().setResult(result);
		},
	);

	const unsubError = globalThis.electronAPI.onNotebookAgentError(
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
