import { create } from "zustand";

/**
 * Result of auto-refactor analysis (matches backend AutoRefactorResult)
 */
export interface AutoRefactorResult {
	analysis: {
		status: string;
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		analysis: any;
		files_analyzed: number;
	};
	plan: {
		status: string;
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		plan: any;
	};
	execution: {
		status: string;
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		execution: any;
		auto_executed: boolean;
	};
	summary: {
		issues_found: number;
		files_analyzed: number;
		refactoring_items: number;
		quick_wins: number;
		estimated_effort: string;
		risk_level: string;
	};
}

export type AutoRefactorPhase =
	| "idle"
	| "analyzing"
	| "complete"
	| "error"
	| "executing";

interface AutoRefactorState {
	// State
	phase: AutoRefactorPhase;
	status: string;
	streamingOutput: string;
	result: AutoRefactorResult | null;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	executionResult: any | null;
	error: string | null;
	isOpen: boolean;
	autoExecute: boolean;
	model?: string;
	thinkingLevel?: string;

	// Actions
	openDialog: (
		autoExecute?: boolean,
		model?: string,
		thinkingLevel?: string,
	) => void;
	closeDialog: () => void;
	setPhase: (phase: AutoRefactorPhase) => void;
	setStatus: (status: string) => void;
	appendStreamingOutput: (chunk: string) => void;
	setResult: (result: AutoRefactorResult) => void;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	setExecutionResult: (result: any) => void;
	setError: (error: string) => void;
	setAutoExecute: (autoExecute: boolean) => void;
	setModel: (model?: string) => void;
	setThinkingLevel: (thinkingLevel?: string) => void;
	reset: () => void;
}

const initialState = {
	phase: "idle" as AutoRefactorPhase,
	status: "",
	streamingOutput: "",
	result: null,
	executionResult: null,
	error: null,
	isOpen: false,
	autoExecute: false,
	model: undefined,
	thinkingLevel: undefined,
};

export const useAutoRefactorStore = create<AutoRefactorState>((set) => ({
	...initialState,

	openDialog: (autoExecute = false, model, thinkingLevel) =>
		set({
			isOpen: true,
			autoExecute,
			model,
			thinkingLevel,
			phase: "idle",
			status: "",
			streamingOutput: "",
			result: null,
			executionResult: null,
			error: null,
		}),

	closeDialog: () =>
		set({
			isOpen: false,
			phase: "idle",
			status: "",
			streamingOutput: "",
			result: null,
			executionResult: null,
			error: null,
		}),

	setPhase: (phase) => set({ phase }),

	setStatus: (status) => set({ status }),

	appendStreamingOutput: (chunk) =>
		set((state) => ({
			streamingOutput: state.streamingOutput + chunk,
		})),

	setResult: (result) =>
		set({
			result,
			phase: "complete",
		}),

	setExecutionResult: (executionResult) =>
		set({
			executionResult,
			phase: "complete",
		}),

	setError: (error) =>
		set({
			error,
			phase: "error",
		}),

	setAutoExecute: (autoExecute) => set({ autoExecute }),

	setModel: (model) => set({ model }),

	setThinkingLevel: (thinkingLevel) => set({ thinkingLevel }),

	reset: () => set(initialState),
}));

/**
 * Start auto-refactor analysis via IPC
 */
export function startAutoRefactor(projectId: string): void {
	const store = useAutoRefactorStore.getState();
	const { autoExecute, model, thinkingLevel } = store;

	// Reset streaming state
	store.setPhase("analyzing");
	store.setStatus("");
	store.appendStreamingOutput(""); // Clear by setting fresh state
	useAutoRefactorStore.setState({
		streamingOutput: "",
		error: null,
		result: null,
		executionResult: null,
	});

	// Send analysis request via IPC
	window.electronAPI.startAutoRefactor({
		projectDir: projectId,
		model,
		thinkingLevel,
		autoExecute,
	});
}

/**
 * Cancel auto-refactor analysis via IPC
 */
export function cancelAutoRefactor(): void {
	window.electronAPI.cancelAutoRefactor();
	useAutoRefactorStore.getState().setPhase("idle");
}

/**
 * Setup IPC listeners for auto-refactor events.
 * Call this once when the app initializes.
 * Returns a cleanup function to unsubscribe all listeners.
 */
export function setupAutoRefactorListeners(): () => void {
	const store = () => useAutoRefactorStore.getState();

	// Listen for streaming chunks
	const unsubChunk = window.electronAPI.onAutoRefactorStreamChunk(
		(chunk: string) => {
			store().appendStreamingOutput(chunk);
		},
	);

	// Listen for status updates
	const unsubStatus = window.electronAPI.onAutoRefactorStatus(
		(status: string) => {
			store().setStatus(status);

			// Update phase based on status
			if (status.includes("Executing") || status.includes("Execution")) {
				store().setPhase("executing");
			} else if (status.includes("Analyzing") || status.includes("Analysis")) {
				store().setPhase("analyzing");
			}
		},
	);

	// Listen for errors
	const unsubError = window.electronAPI.onAutoRefactorError((error: string) => {
		store().setError(error);
	});

	// Listen for analysis completion with structured result
	const unsubComplete = window.electronAPI.onAutoRefactorComplete(
		(result: AutoRefactorResult) => {
			store().setResult(result);
		},
	);

	// Listen for execution completion (if auto-executed)
	const unsubExecutionComplete =
		window.electronAPI.onAutoRefactorExecutionComplete(
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			(result: any) => {
				store().setExecutionResult(result);
			},
		);

	return () => {
		unsubChunk();
		unsubStatus();
		unsubError();
		unsubComplete();
		unsubExecutionComplete();
	};
}

// Helper function to open dialog
export const openAutoRefactorDialog = (autoExecute = false) => {
	useAutoRefactorStore.getState().reset();
	useAutoRefactorStore.getState().openDialog(autoExecute);
};
