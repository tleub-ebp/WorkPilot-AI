import { create } from "zustand";
import type {
	OnboardingAgentEvent,
	OnboardingAgentResult,
	OnboardingPackage,
} from "../../preload/api/modules/onboarding-agent-api";
import type { OnboardingGuide } from "../../shared/types/onboarding";

export type OnboardingAgentPhase = "idle" | "scanning" | "complete" | "error";

interface OnboardingAgentState {
	phase: OnboardingAgentPhase;
	status: string;
	guide: OnboardingGuide | null;
	pkg: OnboardingPackage | null;
	currentTourStep: number;
	quizAnswers: Record<number, number>;
	error: string | null;

	startScan: (projectPath: string) => Promise<void>;
	cancelScan: () => Promise<void>;
	setStatus: (status: string) => void;
	setResult: (result: OnboardingAgentResult) => void;
	setError: (error: string) => void;
	setCurrentTourStep: (idx: number) => void;
	answerQuiz: (qIdx: number, choice: number) => void;
	reset: () => void;
}

export const useOnboardingAgentStore = create<OnboardingAgentState>((set) => ({
	phase: "idle",
	status: "",
	guide: null,
	pkg: null,
	currentTourStep: 0,
	quizAnswers: {},
	error: null,

	startScan: async (projectPath) => {
		if (!projectPath) {
			set({ phase: "error", error: "No project selected" });
			return;
		}
		set({
			phase: "scanning",
			status: "Starting scan...",
			guide: null,
			pkg: null,
			currentTourStep: 0,
			quizAnswers: {},
			error: null,
		});
		try {
			const result = await globalThis.electronAPI.runOnboardingAgentScan({
				projectPath,
			});
			set({
				phase: "complete",
				guide: result.guide,
				pkg: result.package ?? null,
				status: "",
			});
		} catch (err) {
			set({
				phase: "error",
				error: err instanceof Error ? err.message : String(err),
			});
		}
	},

	cancelScan: async () => {
		await globalThis.electronAPI.cancelOnboardingAgentScan();
		set({ phase: "idle", status: "" });
	},

	setStatus: (status) => set({ status }),
	setResult: (result) =>
		set({
			guide: result.guide,
			pkg: result.package ?? null,
			phase: "complete",
		}),
	setError: (error) => set({ error, phase: "error" }),
	setCurrentTourStep: (idx) => set({ currentTourStep: idx }),
	answerQuiz: (qIdx, choice) =>
		set((s) => ({ quizAnswers: { ...s.quizAnswers, [qIdx]: choice } })),
	reset: () =>
		set({
			phase: "idle",
			status: "",
			guide: null,
			pkg: null,
			currentTourStep: 0,
			quizAnswers: {},
			error: null,
		}),
}));

export function setupOnboardingAgentListeners(): () => void {
	const store = () => useOnboardingAgentStore.getState();

	const unsubEvent = globalThis.electronAPI.onOnboardingAgentEvent(
		(event: OnboardingAgentEvent) => {
			if (event?.data?.status) store().setStatus(event.data.status);
		},
	);

	const unsubResult = globalThis.electronAPI.onOnboardingAgentResult(
		(result: OnboardingAgentResult) => {
			store().setResult(result);
		},
	);

	const unsubError = globalThis.electronAPI.onOnboardingAgentError(
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
