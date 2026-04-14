import { create } from "zustand";
import type { I18nAgentEvent } from "../../preload/api/modules/i18n-agent-api";
import type { I18nReport } from "../../shared/types/i18n-agent";

export type I18nAgentPhase = "idle" | "scanning" | "complete" | "error";

interface I18nAgentState {
	phase: I18nAgentPhase;
	status: string;
	report: I18nReport | null;
	error: string | null;
	referenceLocale: string;

	setReferenceLocale: (locale: string) => void;
	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setReport: (report: I18nReport) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useI18nAgentStore = create<I18nAgentState>((set, get) => ({
	phase: "idle",
	status: "",
	report: null,
	error: null,
	referenceLocale: "en",

	setReferenceLocale: (locale) => set({ referenceLocale: locale }),

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
			const report = await globalThis.electronAPI.runI18nScan({
				projectPath,
				referenceLocale: get().referenceLocale,
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
		await globalThis.electronAPI.cancelI18nScan();
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
 * Subscribe the store to runner events. Call once at mount.
 * Returns a cleanup function.
 */
export function setupI18nAgentListeners(): () => void {
	const store = () => useI18nAgentStore.getState();

	const unsubEvent = globalThis.electronAPI.onI18nAgentEvent(
		(event: I18nAgentEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onI18nAgentResult(
		(report: I18nReport) => {
			store().setReport(report);
		},
	);

	const unsubError = globalThis.electronAPI.onI18nAgentError((error: string) => {
		store().setError(error);
	});

	return () => {
		unsubEvent();
		unsubResult();
		unsubError();
	};
}
