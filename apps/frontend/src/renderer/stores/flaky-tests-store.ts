import { create } from "zustand";
import type { FlakyTestsEvent } from "../../preload/api/modules/flaky-tests-api";
import type { FlakyReport } from "../../shared/types/flaky-tests";

export type FlakyTestsPhase = "idle" | "scanning" | "complete" | "error";

interface FlakyTestsState {
	phase: FlakyTestsPhase;
	status: string;
	report: FlakyReport | null;
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setReport: (report: FlakyReport) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useFlakyTestsStore = create<FlakyTestsState>((set) => ({
	phase: "idle",
	status: "",
	report: null,
	error: null,

	startScan: async (projectPath) => {
		if (!projectPath) {
			set({ phase: "error", error: "No project selected" });
			return;
		}
		set({
			phase: "scanning",
			status: "Starting scan...",
			report: null,
			error: null,
		});
		try {
			const report = await globalThis.electronAPI.runFlakyTestsScan({
				projectPath,
			});
			set({ phase: "complete", report, status: "" });
		} catch (err) {
			set({
				phase: "error",
				error: err instanceof Error ? err.message : String(err),
			});
		}
	},

	cancelScan: async () => {
		await globalThis.electronAPI.cancelFlakyTestsScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setReport: (report) => set({ report, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", report: null, error: null }),
}));

export function setupFlakyTestsListeners(): () => void {
	const store = () => useFlakyTestsStore.getState();

	const unsubEvent = globalThis.electronAPI.onFlakyTestsEvent(
		(event: FlakyTestsEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onFlakyTestsResult(
		(report: FlakyReport) => {
			store().setReport(report);
		},
	);

	const unsubError = globalThis.electronAPI.onFlakyTestsError(
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
