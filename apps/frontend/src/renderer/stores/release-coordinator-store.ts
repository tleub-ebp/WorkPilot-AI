import { create } from "zustand";
import type { ReleaseTrainPlan } from "../../shared/types/release-coordinator";
import type { ReleaseCoordinatorEvent } from "../../preload/api/modules/release-coordinator-api";

export type ReleaseCoordinatorPhase =
	| "idle"
	| "planning"
	| "complete"
	| "error";

interface ReleaseCoordinatorState {
	phase: ReleaseCoordinatorPhase;
	status: string;
	plan: ReleaseTrainPlan | null;
	error: string | null;

	startPlan: (projectPath: string) => Promise<void>;
	cancelPlan: () => Promise<void>;
	setStatus: (status: string) => void;
	setPlan: (plan: ReleaseTrainPlan) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useReleaseCoordinatorStore = create<ReleaseCoordinatorState>(
	(set) => ({
		phase: "idle",
		status: "",
		plan: null,
		error: null,

		startPlan: async (projectPath) => {
			if (!projectPath) {
				set({ phase: "error", error: "No project selected" });
				return;
			}
			set({
				phase: "planning",
				status: "Starting plan...",
				plan: null,
				error: null,
			});
			try {
				const plan = await globalThis.electronAPI.runReleaseCoordinatorPlan({
					projectPath,
				});
				set({ phase: "complete", plan, status: "" });
			} catch (err) {
				set({
					phase: "error",
					error: err instanceof Error ? err.message : String(err),
				});
			}
		},

		cancelPlan: async () => {
			await globalThis.electronAPI.cancelReleaseCoordinatorPlan();
			set({ phase: "idle", status: "" });
		},

		setStatus: (status) => set({ status }),
		setPlan: (plan) => set({ plan, phase: "complete" }),
		setError: (error) => set({ error, phase: "error" }),
		reset: () => set({ phase: "idle", status: "", plan: null, error: null }),
	}),
);

export function setupReleaseCoordinatorListeners(): () => void {
	const store = () => useReleaseCoordinatorStore.getState();

	const unsubEvent = globalThis.electronAPI.onReleaseCoordinatorEvent(
		(event: ReleaseCoordinatorEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onReleaseCoordinatorResult(
		(plan: ReleaseTrainPlan) => {
			store().setPlan(plan);
		},
	);

	const unsubError = globalThis.electronAPI.onReleaseCoordinatorError(
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
