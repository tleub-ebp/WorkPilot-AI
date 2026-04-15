import { create } from "zustand";
import type {
	SandboxEvent,
	SandboxResult,
} from "../../preload/api/modules/sandbox-api";
import type { SimulationResult } from "../../shared/types/sandbox";

export type SandboxPhaseUI = "idle" | "scanning" | "complete" | "error";

interface SandboxState {
	phase: SandboxPhaseUI;
	status: string;
	result: SimulationResult | null;
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setResult: (payload: SandboxResult) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useSandboxStore = create<SandboxState>((set) => ({
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
			status: "Starting scan...",
			result: null,
			error: null,
		});
		try {
			const payload = await globalThis.electronAPI.runSandboxScan({
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
		await globalThis.electronAPI.cancelSandboxScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setResult: (payload) => set({ result: payload.result, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", result: null, error: null }),
}));

export function setupSandboxListeners(): () => void {
	const store = () => useSandboxStore.getState();

	const unsubEvent = globalThis.electronAPI.onSandboxEvent(
		(event: SandboxEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onSandboxResult(
		(payload: SandboxResult) => {
			store().setResult(payload);
		},
	);

	const unsubError = globalThis.electronAPI.onSandboxError((error: string) => {
		store().setError(error);
	});

	return () => {
		unsubEvent();
		unsubResult();
		unsubError();
	};
}
