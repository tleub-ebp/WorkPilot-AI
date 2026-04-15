import { create } from "zustand";
import type {
	InjectionGuardEvent,
	InjectionGuardScanResult,
} from "../../preload/api/modules/injection-guard-api";
import type { InjectionScanResult } from "../../shared/types/injection-guard";

export type InjectionGuardPhase = "idle" | "scanning" | "complete" | "error";

interface InjectionGuardState {
	phase: InjectionGuardPhase;
	status: string;
	results: InjectionScanResult[];
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setResult: (result: InjectionGuardScanResult) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useInjectionGuardStore = create<InjectionGuardState>((set) => ({
	phase: "idle",
	status: "",
	results: [],
	error: null,

	startScan: async (projectPath) => {
		if (!projectPath) {
			set({ phase: "error", error: "No project selected" });
			return;
		}
		set({
			phase: "scanning",
			status: "Starting scan...",
			results: [],
			error: null,
		});
		try {
			const payload = await globalThis.electronAPI.runInjectionGuardScan({
				projectPath,
			});
			set({ phase: "complete", results: payload.results, status: "" });
		} catch (err) {
			set({
				phase: "error",
				error: err instanceof Error ? err.message : String(err),
			});
		}
	},

	cancelScan: async () => {
		await globalThis.electronAPI.cancelInjectionGuardScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setResult: (result) => set({ results: result.results, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", results: [], error: null }),
}));

export function setupInjectionGuardListeners(): () => void {
	const store = () => useInjectionGuardStore.getState();

	const unsubEvent = globalThis.electronAPI.onInjectionGuardEvent(
		(event: InjectionGuardEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onInjectionGuardResult(
		(result: InjectionGuardScanResult) => {
			store().setResult(result);
		},
	);

	const unsubError = globalThis.electronAPI.onInjectionGuardError(
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
