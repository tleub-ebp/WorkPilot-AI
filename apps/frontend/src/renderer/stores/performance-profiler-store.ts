import { create } from "zustand";
import type { PerformanceProfilerResult } from "../../main/performance-profiler-service";

export type PerformanceProfilerPhase =
	| "idle"
	| "profiling"
	| "analyzing"
	| "optimizing"
	| "complete"
	| "error";

interface PerformanceProfilerState {
	phase: PerformanceProfilerPhase;
	status: string;
	streamingOutput: string;
	result: PerformanceProfilerResult | null;
	implementationResult: unknown;
	error: string | null;
	isOpen: boolean;
	autoImplement: boolean;
	model?: string;
	thinkingLevel?: string;

	openDashboard: () => void;
	closeDashboard: () => void;
	setPhase: (phase: PerformanceProfilerPhase) => void;
	setStatus: (status: string) => void;
	appendStreamingOutput: (chunk: string) => void;
	setResult: (result: PerformanceProfilerResult) => void;
	setImplementationResult: (result: unknown) => void;
	setError: (error: string) => void;
	setAutoImplement: (value: boolean) => void;
	setModel: (model?: string) => void;
	setThinkingLevel: (level?: string) => void;
	reset: () => void;
}

const initialState = {
	phase: "idle" as PerformanceProfilerPhase,
	status: "",
	streamingOutput: "",
	result: null,
	implementationResult: null,
	error: null,
	isOpen: false,
	autoImplement: false,
	model: undefined,
	thinkingLevel: undefined,
};

export const usePerformanceProfilerStore = create<PerformanceProfilerState>(
	(set) => ({
		...initialState,

		openDashboard: () => set({ isOpen: true }),
		closeDashboard: () =>
			set({
				isOpen: false,
				phase: "idle",
				status: "",
				streamingOutput: "",
				result: null,
				error: null,
			}),
		setPhase: (phase) => set({ phase }),
		setStatus: (status) => set({ status }),
		appendStreamingOutput: (chunk) =>
			set((s) => ({ streamingOutput: s.streamingOutput + chunk })),
		setResult: (result) => set({ result, phase: "complete" }),
		setImplementationResult: (implementationResult) =>
			set({ implementationResult }),
		setError: (error) => set({ error, phase: "error" }),
		setAutoImplement: (autoImplement) => set({ autoImplement }),
		setModel: (model) => set({ model }),
		setThinkingLevel: (thinkingLevel) => set({ thinkingLevel }),
		reset: () => set(initialState),
	}),
);

export function startPerformanceProfiling(projectDir: string): void {
	const store = usePerformanceProfilerStore.getState();
	store.setPhase("profiling");
	usePerformanceProfilerStore.setState({
		streamingOutput: "",
		error: null,
		result: null,
		implementationResult: null,
	});

	window.electronAPI.startPerformanceProfiling({
		projectDir,
		autoImplement: store.autoImplement,
		model: store.model,
		thinkingLevel: store.thinkingLevel,
	});
}

export function cancelPerformanceProfiling(): void {
	window.electronAPI.cancelPerformanceProfiling();
	usePerformanceProfilerStore.getState().setPhase("idle");
}

export function setupPerformanceProfilerListeners(): () => void {
	const store = () => usePerformanceProfilerStore.getState();

	const unsubChunk = window.electronAPI.onPerformanceProfilerStreamChunk(
		(chunk: string) => {
			store().appendStreamingOutput(chunk);
		},
	);

	const unsubStatus = window.electronAPI.onPerformanceProfilerStatus(
		(status: string) => {
			store().setStatus(status);
			if (
				status.toLowerCase().includes("phase 1") ||
				status.toLowerCase().includes("detect")
			) {
				store().setPhase("profiling");
			} else if (
				status.toLowerCase().includes("phase 2") ||
				status.toLowerCase().includes("benchmark")
			) {
				store().setPhase("analyzing");
			} else if (
				status.toLowerCase().includes("phase 3") ||
				status.toLowerCase().includes("suggest")
			) {
				store().setPhase("optimizing");
			}
		},
	);

	const unsubError = window.electronAPI.onPerformanceProfilerError(
		(error: string) => {
			store().setError(error);
		},
	);

	const unsubComplete = window.electronAPI.onPerformanceProfilerComplete(
		(result: PerformanceProfilerResult) => {
			store().setResult(result);
		},
	);

	const unsubImpl =
		window.electronAPI.onPerformanceProfilerImplementationComplete(
			(result: unknown) => {
				store().setImplementationResult(result);
			},
		);

	return () => {
		unsubChunk();
		unsubStatus();
		unsubError();
		unsubComplete();
		unsubImpl();
	};
}
