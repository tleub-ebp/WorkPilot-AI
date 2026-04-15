import { create } from "zustand";
import type { SurgeryPlan } from "../../shared/types/git-surgeon";
import type { GitSurgeonEvent } from "../../preload/api/modules/git-surgeon-api";

export type GitSurgeonPhase = "idle" | "scanning" | "complete" | "error";

interface GitSurgeonState {
	phase: GitSurgeonPhase;
	status: string;
	plan: SurgeryPlan | null;
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setPlan: (plan: SurgeryPlan) => void;
	setError: (error: string) => void;
	reset: () => void;
}

export const useGitSurgeonStore = create<GitSurgeonState>((set) => ({
	phase: "idle",
	status: "",
	plan: null,
	error: null,

	startScan: async (projectPath) => {
		if (!projectPath) {
			set({ phase: "error", error: "No project selected" });
			return;
		}
		set({
			phase: "scanning",
			status: "Starting analysis...",
			plan: null,
			error: null,
		});
		try {
			const plan = await globalThis.electronAPI.runGitSurgeonScan({
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

	cancelScan: async () => {
		await globalThis.electronAPI.cancelGitSurgeonScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setPlan: (plan) => set({ plan, phase: "complete" }),
	setError: (error) => set({ error, phase: "error" }),
	reset: () => set({ phase: "idle", status: "", plan: null, error: null }),
}));

export function setupGitSurgeonListeners(): () => void {
	const store = () => useGitSurgeonStore.getState();

	const unsubEvent = globalThis.electronAPI.onGitSurgeonEvent(
		(event: GitSurgeonEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onGitSurgeonResult(
		(plan: SurgeryPlan) => {
			store().setPlan(plan);
		},
	);

	const unsubError = globalThis.electronAPI.onGitSurgeonError(
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
