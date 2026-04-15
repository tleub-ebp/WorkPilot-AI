import { create } from "zustand";
import type { ComplianceEvent } from "../../preload/api/modules/compliance-api";
import type {
	ComplianceFramework,
	ComplianceReport,
} from "../../shared/types/compliance";

export type CompliancePhase = "idle" | "scanning" | "complete" | "error";

interface ComplianceState {
	phase: CompliancePhase;
	status: string;
	report: ComplianceReport | null;
	error: string | null;
	framework: ComplianceFramework;

	setFramework: (framework: ComplianceFramework) => void;
	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setReport: (report: ComplianceReport) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useComplianceStore = create<ComplianceState>((set, get) => ({
	phase: "idle",
	status: "",
	report: null,
	error: null,
	framework: "SOC2",

	setFramework: (framework) => set({ framework }),

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
			const report = await globalThis.electronAPI.runComplianceScan({
				projectPath,
				framework: get().framework,
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
		await globalThis.electronAPI.cancelComplianceScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setReport: (report) => set({ report, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", report: null, error: null }),
}));

export function setupComplianceListeners(): () => void {
	const store = () => useComplianceStore.getState();

	const unsubEvent = globalThis.electronAPI.onComplianceEvent(
		(event: ComplianceEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onComplianceResult(
		(report: ComplianceReport) => {
			store().setReport(report);
		},
	);

	const unsubError = globalThis.electronAPI.onComplianceError(
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
