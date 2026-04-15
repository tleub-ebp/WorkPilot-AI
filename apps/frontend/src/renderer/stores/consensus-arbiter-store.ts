import { create } from "zustand";
import type {
	ConsensusArbiterEvent,
	ConsensusArbiterScanResult,
} from "../../preload/api/modules/consensus-arbiter-api";
import type { ConsensusResult } from "../../shared/types/consensus-arbiter";

export type ConsensusArbiterPhase =
	| "idle"
	| "scanning"
	| "complete"
	| "error";

interface ConsensusArbiterState {
	phase: ConsensusArbiterPhase;
	status: string;
	result: ConsensusResult | null;
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setResult: (result: ConsensusArbiterScanResult) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useConsensusArbiterStore = create<ConsensusArbiterState>(
	(set) => ({
		phase: "idle",
		status: "",
		result: null,
		error: null,

		startScan: async (projectPath) => {
			if (!projectPath) {
				set({ phase: "error", error: "No project selected" });
				return;
			}
			set({
				phase: "scanning",
				status: "Starting arbitration...",
				result: null,
				error: null,
			});
			try {
				const payload = await globalThis.electronAPI.runConsensusArbiterScan({
					projectPath,
				});
				set({ phase: "complete", result: payload.result, status: "" });
			} catch (err) {
				set({
					phase: "error",
					error: err instanceof Error ? err.message : String(err),
				});
			}
		},

		cancelScan: async () => {
			await globalThis.electronAPI.cancelConsensusArbiterScan();
			set({ phase: "idle", status: "" });
		},

		setStatus: (status) => set({ status }),
		setResult: (result) =>
			set({ result: result.result, phase: "complete" }),
		setError: (error) => set({ error, phase: "error" }),
		reset: () => set({ phase: "idle", status: "", result: null, error: null }),
	}),
);

export function setupConsensusArbiterListeners(): () => void {
	const store = () => useConsensusArbiterStore.getState();

	const unsubEvent = globalThis.electronAPI.onConsensusArbiterEvent(
		(event: ConsensusArbiterEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onConsensusArbiterResult(
		(result: ConsensusArbiterScanResult) => {
			store().setResult(result);
		},
	);

	const unsubError = globalThis.electronAPI.onConsensusArbiterError(
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
