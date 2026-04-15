import { create } from "zustand";
import type {
	RegressionGuardianEvent,
	RegressionGuardianScanResult,
} from "../../preload/api/modules/regression-guardian-api";
import type { RegressionGuardianResult } from "../../shared/types/regression-guardian";

export type RegressionGuardianPhase =
	| "idle"
	| "scanning"
	| "complete"
	| "error";

interface RegressionGuardianState {
	phase: RegressionGuardianPhase;
	status: string;
	results: RegressionGuardianResult[];
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setResult: (result: RegressionGuardianScanResult) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useRegressionGuardianStore = create<RegressionGuardianState>(
	(set) => ({
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
				const payload = await globalThis.electronAPI.runRegressionGuardianScan({
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
			await globalThis.electronAPI.cancelRegressionGuardianScan();
			set({ phase: "idle", status: "" });
		},

		setStatus: (status) => set({ status }),
		setResult: (result) =>
			set({ results: result.results, phase: "complete" }),
		setError: (error) => set({ error, phase: "error" }),
		reset: () => set({ phase: "idle", status: "", results: [], error: null }),
	}),
);

export function setupRegressionGuardianListeners(): () => void {
	const store = () => useRegressionGuardianStore.getState();

	const unsubEvent = globalThis.electronAPI.onRegressionGuardianEvent(
		(event: RegressionGuardianEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onRegressionGuardianResult(
		(result: RegressionGuardianScanResult) => {
			store().setResult(result);
		},
	);

	const unsubError = globalThis.electronAPI.onRegressionGuardianError(
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
