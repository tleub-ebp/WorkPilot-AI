import { create } from "zustand";

/**
 * Result of smart estimation analysis
 */
export interface SmartEstimationResult {
	complexity_score: number;
	confidence_level: number;
	reasoning: string[];
	similar_tasks: Array<{
		build_id: string;
		spec_name: string;
		similarity_score: number;
		complexity_score: number;
		duration_hours?: number;
		qa_iterations?: number;
		success_rate?: number;
		tokens_used?: number;
		cost_usd?: number;
		status: string;
	}>;
	risk_factors: string[];
	estimated_duration_hours?: number;
	estimated_qa_iterations?: number;
	token_cost_estimate?: number;
	recommendations: string[];
}

export type SmartEstimationPhase = "idle" | "analyzing" | "complete" | "error";

interface SmartEstimationState {
	// State
	phase: SmartEstimationPhase;
	status: string;
	streamingOutput: string;
	result: SmartEstimationResult | null;
	error: string | null;
	isOpen: boolean;
	initialTaskDescription: string;

	// Actions
	openDialog: (taskDescription: string) => void;
	closeDialog: () => void;
	setPhase: (phase: SmartEstimationPhase) => void;
	setStatus: (status: string) => void;
	appendStreamingOutput: (chunk: string) => void;
	setResult: (result: SmartEstimationResult) => void;
	setError: (error: string) => void;
	reset: () => void;
}

const initialState = {
	phase: "idle" as SmartEstimationPhase,
	status: "",
	streamingOutput: "",
	result: null,
	error: null as string | null,
	isOpen: false,
	initialTaskDescription: "",
};

export const useSmartEstimationStore = create<SmartEstimationState>((set) => ({
	...initialState,

	openDialog: (taskDescription) =>
		set({
			isOpen: true,
			initialTaskDescription: taskDescription,
			phase: "idle",
			status: "",
			streamingOutput: "",
			result: null,
			error: null,
		}),

	closeDialog: () =>
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
		set((state) => ({
			streamingOutput: state.streamingOutput + chunk,
		})),

	setResult: (result) =>
		set({
			result,
			phase: "complete",
		}),

	setError: (error) =>
		set({
			error,
			phase: "error",
		}),

	reset: () => set(initialState),
}));

/**
 * Start smart estimation via IPC
 */
export function startSmartEstimation(projectId: string): void {
	const store = useSmartEstimationStore.getState();
	const { initialTaskDescription } = store;

	if (!projectId || !initialTaskDescription.trim()) return;

	// Reset streaming state
	store.setPhase("analyzing");
	store.setStatus("");
	store.appendStreamingOutput(""); // Clear by setting fresh state
	useSmartEstimationStore.setState({
		streamingOutput: "",
		error: null,
		result: null,
	});

	// Send estimation request via IPC
	globalThis.electronAPI.runSmartEstimation(projectId, initialTaskDescription);
}

/**
 * Setup IPC listeners for smart estimation events.
 * Call this once when the app initializes.
 * Returns a cleanup function to unsubscribe all listeners.
 */
export function setupSmartEstimationListeners(): () => void {
	const store = () => useSmartEstimationStore.getState();

	// Listen for streaming chunks
	const unsubChunk = globalThis.electronAPI.onSmartEstimationStreamChunk(
		(chunk: string) => {
			store().appendStreamingOutput(chunk);
		},
	);

	// Listen for status updates
	const unsubStatus = globalThis.electronAPI.onSmartEstimationStatus(
		(status: string) => {
			store().setStatus(status);
		},
	);

	// Listen for errors
	const unsubError = globalThis.electronAPI.onSmartEstimationError(
		(error: string) => {
			store().setError(error);
		},
	);

	// Listen for completion with structured result
	const unsubComplete = globalThis.electronAPI.onSmartEstimationComplete(
		(result: SmartEstimationResult) => {
			store().setResult(result);
		},
	);

	// Listen for events (for future extensibility)
	const unsubEvent = globalThis.electronAPI.onSmartEstimationEvent(
		(_event: unknown) => {
			/* intentionally empty */
		},
	);

	return () => {
		unsubChunk();
		unsubStatus();
		unsubError();
		unsubComplete();
		unsubEvent();
	};
}
