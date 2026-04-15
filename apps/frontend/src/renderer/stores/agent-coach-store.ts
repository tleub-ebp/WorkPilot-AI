import { create } from "zustand";
import type {
	AgentCoachEvent,
	AgentCoachResult,
} from "../../preload/api/modules/agent-coach-api";
import type { CoachReport } from "../../shared/types/agent-coach";

export type AgentCoachPhase = "idle" | "scanning" | "complete" | "error";

interface AgentCoachState {
	phase: AgentCoachPhase;
	status: string;
	report: CoachReport | null;
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setResult: (result: AgentCoachResult) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useAgentCoachStore = create<AgentCoachState>((set) => ({
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
			const result = await globalThis.electronAPI.runAgentCoachScan({
				projectPath,
			});
			set({ phase: "complete", report: result.report, status: "" });
		} catch (err) {
			set({
				phase: "error",
				error: err instanceof Error ? err.message : String(err),
			});
		}
	},

	cancelScan: async () => {
		await globalThis.electronAPI.cancelAgentCoachScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setResult: (result) => set({ report: result.report, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", report: null, error: null }),
}));

export function setupAgentCoachListeners(): () => void {
	const store = () => useAgentCoachStore.getState();

	const unsubEvent = globalThis.electronAPI.onAgentCoachEvent(
		(event: AgentCoachEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onAgentCoachResult(
		(result: AgentCoachResult) => {
			store().setResult(result);
		},
	);

	const unsubError = globalThis.electronAPI.onAgentCoachError(
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
