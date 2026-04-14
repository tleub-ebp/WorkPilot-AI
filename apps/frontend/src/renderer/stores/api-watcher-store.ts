import { create } from "zustand";
import type {
	ApiWatcherEvent,
	ApiWatcherResult,
} from "../../preload/api/modules/api-watcher-api";

export type ApiWatcherPhase = "idle" | "scanning" | "complete" | "error";

interface ApiWatcherState {
	phase: ApiWatcherPhase;
	status: string;
	result: ApiWatcherResult | null;
	error: string | null;

	startScan: (projectPath: string, saveBaseline?: boolean) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setResult: (result: ApiWatcherResult) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useApiWatcherStore = create<ApiWatcherState>((set) => ({
	phase: "idle",
	status: "",
	result: null,
	error: null,

	startScan: async (projectPath, saveBaseline = false) => {
		if (!projectPath) {
			set({ phase: "error", error: "No project selected" });
			return;
		}
		set({
			phase: "scanning",
			status: "Starting scan...",
			result: null,
			error: null,
		});
		try {
			const result = await globalThis.electronAPI.runApiWatcherScan({
				projectPath,
				saveBaseline,
			});
			set({ phase: "complete", result, status: "" });
		} catch (err) {
			set({
				phase: "error",
				error: err instanceof Error ? err.message : String(err),
			});
		}
	},

	cancelScan: async () => {
		await globalThis.electronAPI.cancelApiWatcherScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setResult: (result) => set({ result, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", result: null, error: null }),
}));

export function setupApiWatcherListeners(): () => void {
	const store = () => useApiWatcherStore.getState();

	const unsubEvent = globalThis.electronAPI.onApiWatcherEvent(
		(event: ApiWatcherEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onApiWatcherResult(
		(result: ApiWatcherResult) => {
			store().setResult(result);
		},
	);

	const unsubError = globalThis.electronAPI.onApiWatcherError(
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
