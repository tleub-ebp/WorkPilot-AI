import { create } from "zustand";

/**
 * Result of prompt optimization (matches backend PromptOptimizerResult)
 */
export interface PromptOptimizerResult {
	optimized: string;
	changes: string[];
	reasoning: string;
}

export type AgentType = "analysis" | "coding" | "verification" | "general";

export type PromptOptimizerPhase = "idle" | "optimizing" | "complete" | "error";

interface PromptOptimizerState {
	// State
	phase: PromptOptimizerPhase;
	status: string;
	streamingOutput: string;
	result: PromptOptimizerResult | null;
	error: string | null;
	isOpen: boolean;
	initialPrompt: string;
	agentType: AgentType;

	// Actions
	openDialog: (prompt: string, agentType?: AgentType) => void;
	closeDialog: () => void;
	setPhase: (phase: PromptOptimizerPhase) => void;
	setStatus: (status: string) => void;
	appendStreamingOutput: (chunk: string) => void;
	setResult: (result: PromptOptimizerResult) => void;
	setError: (error: string) => void;
	setAgentType: (agentType: AgentType) => void;
	reset: () => void;
}

const initialState = {
	phase: "idle" as PromptOptimizerPhase,
	status: "",
	streamingOutput: "",
	result: null,
	error: null,
	isOpen: false,
	initialPrompt: "",
	agentType: "general" as const,
};

export const usePromptOptimizerStore = create<PromptOptimizerState>((set) => ({
	...initialState,

	openDialog: (prompt, agentType = "general") =>
		set({
			isOpen: true,
			initialPrompt: prompt,
			agentType,
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

	setAgentType: (agentType) => set({ agentType }),

	reset: () => set(initialState),
}));

/**
 * Start prompt optimization via IPC
 */
export function startOptimization(projectId: string): void {
	const store = usePromptOptimizerStore.getState();
	const { initialPrompt, agentType } = store;

	if (!initialPrompt.trim()) return;

	// Reset streaming state
	store.setPhase("optimizing");
	store.setStatus("");
	store.appendStreamingOutput(""); // Clear by setting fresh state
	usePromptOptimizerStore.setState({
		streamingOutput: "",
		error: null,
		result: null,
	});

	// Send optimization request via IPC
	globalThis.electronAPI.optimizePrompt(projectId, initialPrompt, agentType);
}

/**
 * Setup IPC listeners for prompt optimizer events.
 * Call this once when the app initializes.
 * Returns a cleanup function to unsubscribe all listeners.
 */
export function setupPromptOptimizerListeners(): () => void {
	const store = () => usePromptOptimizerStore.getState();

	// Listen for streaming chunks
	const unsubChunk = globalThis.electronAPI.onPromptOptimizerStreamChunk(
		(chunk: string) => {
			store().appendStreamingOutput(chunk);
		},
	);

	// Listen for status updates
	const unsubStatus = globalThis.electronAPI.onPromptOptimizerStatus(
		(status: string) => {
			store().setStatus(status);
		},
	);

	// Listen for errors
	const unsubError = globalThis.electronAPI.onPromptOptimizerError(
		(error: string) => {
			store().setError(error);
		},
	);

	// Listen for completion with structured result
	const unsubComplete = globalThis.electronAPI.onPromptOptimizerComplete(
		(result: PromptOptimizerResult) => {
			store().setResult(result);
		},
	);

	return () => {
		unsubChunk();
		unsubStatus();
		unsubError();
		unsubComplete();
	};
}

// Helper function to open dialog
export const openPromptOptimizerDialog = () => {
	const store = usePromptOptimizerStore.getState();
	store.reset();
	store.openDialog("", "general");
};
