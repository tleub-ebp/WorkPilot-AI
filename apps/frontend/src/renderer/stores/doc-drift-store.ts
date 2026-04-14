import { create } from "zustand";
import type { DocDriftEvent } from "../../preload/api/modules/doc-drift-api";
import type { DriftReport } from "../../shared/types/doc-drift";

export type DocDriftPhase = "idle" | "scanning" | "complete" | "error";

interface DocDriftState {
	phase: DocDriftPhase;
	status: string;
	report: DriftReport | null;
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setReport: (report: DriftReport) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useDocDriftStore = create<DocDriftState>((set) => ({
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
			const report = await globalThis.electronAPI.runDocDriftScan({ projectPath });
			set({ phase: "complete", report, status: "" });
		} catch (err) {
			set({
				phase: "error",
				error: err instanceof Error ? err.message : String(err),
			});
		}
	},

	cancelScan: async () => {
		await globalThis.electronAPI.cancelDocDriftScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setReport: (report) => set({ report, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", report: null, error: null }),
}));

export function setupDocDriftListeners(): () => void {
	const store = () => useDocDriftStore.getState();

	const unsubEvent = globalThis.electronAPI.onDocDriftEvent(
		(event: DocDriftEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onDocDriftResult(
		(report: DriftReport) => {
			store().setReport(report);
		},
	);

	const unsubError = globalThis.electronAPI.onDocDriftError((error: string) => {
		store().setError(error);
	});

	return () => {
		unsubEvent();
		unsubResult();
		unsubError();
	};
}
