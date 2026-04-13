import { create } from "zustand";
import type { AccessibilityEvent } from "../../preload/api/modules/accessibility-api";
import type { A11yReport } from "../../shared/types/accessibility";

export type AccessibilityPhase = "idle" | "scanning" | "complete" | "error";

export type WcagTargetLevel = "A" | "AA" | "AAA";

interface AccessibilityState {
	phase: AccessibilityPhase;
	status: string;
	report: A11yReport | null;
	error: string | null;
	targetLevel: WcagTargetLevel;

	setTargetLevel: (level: WcagTargetLevel) => void;
	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setReport: (report: A11yReport) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useAccessibilityStore = create<AccessibilityState>((set, get) => ({
	phase: "idle",
	status: "",
	report: null,
	error: null,
	targetLevel: "AA",

	setTargetLevel: (level) => set({ targetLevel: level }),

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
			const report = await globalThis.electronAPI.runAccessibilityScan({
				projectPath,
				targetLevel: get().targetLevel,
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
		await globalThis.electronAPI.cancelAccessibilityScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setReport: (report) => set({ report, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () =>
		set({
			phase: "idle",
			status: "",
			report: null,
			error: null,
		}),
}));

/**
 * Subscribe the store to runner events. Call once at app startup.
 * Returns a cleanup function.
 */
export function setupAccessibilityListeners(): () => void {
	const store = () => useAccessibilityStore.getState();

	const unsubEvent = globalThis.electronAPI.onAccessibilityEvent(
		(event: AccessibilityEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onAccessibilityResult(
		(report: A11yReport) => {
			store().setReport(report);
		},
	);

	const unsubError = globalThis.electronAPI.onAccessibilityError(
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
