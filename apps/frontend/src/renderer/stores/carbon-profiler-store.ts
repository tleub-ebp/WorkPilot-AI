import { create } from "zustand";
import type { CarbonProfilerEvent } from "../../preload/api/modules/carbon-profiler-api";
import type { CarbonReport } from "../../shared/types/carbon-profiler";

export type CarbonProfilerPhase = "idle" | "scanning" | "complete" | "error";

interface CarbonProfilerState {
	phase: CarbonProfilerPhase;
	status: string;
	report: CarbonReport | null;
	error: string | null;
	region: string;

	setRegion: (region: string) => void;
	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setReport: (report: CarbonReport) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useCarbonProfilerStore = create<CarbonProfilerState>((set, get) => ({
	phase: "idle",
	status: "",
	report: null,
	error: null,
	region: "global_avg",

	setRegion: (region) => set({ region }),

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
			const report = await globalThis.electronAPI.runCarbonProfilerScan({
				projectPath,
				region: get().region,
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
		await globalThis.electronAPI.cancelCarbonProfilerScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setReport: (report) => set({ report, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", report: null, error: null }),
}));

export function setupCarbonProfilerListeners(): () => void {
	const store = () => useCarbonProfilerStore.getState();

	const unsubEvent = globalThis.electronAPI.onCarbonProfilerEvent(
		(event: CarbonProfilerEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onCarbonProfilerResult(
		(report: CarbonReport) => {
			store().setReport(report);
		},
	);

	const unsubError = globalThis.electronAPI.onCarbonProfilerError(
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
