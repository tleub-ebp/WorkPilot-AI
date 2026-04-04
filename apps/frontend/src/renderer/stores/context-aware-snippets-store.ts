import { create } from "zustand";

/**
 * Result of context-aware snippet generation (matches backend ContextAwareSnippetResult)
 */
export interface ContextAwareSnippetResult {
	snippet: string;
	language: string;
	description: string;
	context_used: string[];
	adaptations: string[];
	reasoning: string;
}

export type ContextAwareSnippetsPhase =
	| "idle"
	| "generating"
	| "complete"
	| "error";

export type SnippetType =
	| "component"
	| "function"
	| "class"
	| "hook"
	| "utility"
	| "api"
	| "test";

interface ContextAwareSnippetsState {
	// State
	phase: ContextAwareSnippetsPhase;
	status: string;
	streamingOutput: string;
	result: ContextAwareSnippetResult | null;
	error: string | null;
	isOpen: boolean;
	snippetType: SnippetType;
	description: string;
	language: string;
	autoDetectLanguage: boolean;

	// Actions
	openDialog: (
		snippetType?: SnippetType,
		description?: string,
		language?: string,
	) => void;
	closeDialog: () => void;
	setPhase: (phase: ContextAwareSnippetsPhase) => void;
	setStatus: (status: string) => void;
	appendStreamingOutput: (chunk: string) => void;
	setResult: (result: ContextAwareSnippetResult) => void;
	setError: (error: string) => void;
	setSnippetType: (snippetType: SnippetType) => void;
	setDescription: (description: string) => void;
	setLanguage: (language: string) => void;
	setAutoDetectLanguage: (autoDetect: boolean) => void;
	reset: () => void;
}

const initialState = {
	phase: "idle" as ContextAwareSnippetsPhase,
	status: "",
	streamingOutput: "",
	result: null,
	error: null,
	isOpen: false,
	snippetType: "component" as const,
	description: "",
	language: "",
	autoDetectLanguage: true,
};

export const useContextAwareSnippetsStore = create<ContextAwareSnippetsState>(
	(set) => ({
		...initialState,

		openDialog: (snippetType = "component", description = "", language = "") =>
			set({
				isOpen: true,
				snippetType,
				description,
				language,
				autoDetectLanguage: !language,
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

		setSnippetType: (snippetType) => set({ snippetType }),

		setDescription: (description) => set({ description }),

		setLanguage: (language) => set({ language }),

		setAutoDetectLanguage: (autoDetect) =>
			set({ autoDetectLanguage: autoDetect }),

		reset: () => set(initialState),
	}),
);

/**
 * Start snippet generation via IPC
 */
export function startSnippetGeneration(projectId: string): void {
	const store = useContextAwareSnippetsStore.getState();
	const { snippetType, description, language, autoDetectLanguage } = store;

	if (!description.trim()) return;

	// Reset streaming state
	store.setPhase("generating");
	store.setStatus("");
	store.appendStreamingOutput(""); // Clear by setting fresh state
	useContextAwareSnippetsStore.setState({
		streamingOutput: "",
		error: null,
		result: null,
	});

	// Send generation request via IPC
	globalThis.electronAPI.generateContextAwareSnippet(
		projectId,
		snippetType,
		description,
		autoDetectLanguage ? undefined : language,
	);
}

/**
 * Setup IPC listeners for context-aware snippets events.
 * Call this once when the app initializes.
 * Returns a cleanup function to unsubscribe all listeners.
 */
export function setupContextAwareSnippetsListeners(): () => void {
	const store = () => useContextAwareSnippetsStore.getState();

	// Listen for streaming chunks
	const unsubChunk = globalThis.electronAPI.onSnippetStreamChunk(
		(chunk: string) => {
			store().appendStreamingOutput(chunk);
		},
	);

	// Listen for status updates
	const unsubStatus = globalThis.electronAPI.onSnippetStatus(
		(status: string) => {
			store().setStatus(status);
		},
	);

	// Listen for errors
	const unsubError = globalThis.electronAPI.onSnippetError((error: string) => {
		store().setError(error);
	});

	// Listen for completion with structured result
	const unsubComplete = globalThis.electronAPI.onSnippetComplete(
		(result: ContextAwareSnippetResult) => {
			store().setResult(result);
		},
	);

	return () => {
		// Only call cleanup functions if they exist and are functions
		if (typeof unsubChunk === "function") unsubChunk();
		if (typeof unsubStatus === "function") unsubStatus();
		if (typeof unsubError === "function") unsubError();
		if (typeof unsubComplete === "function") unsubComplete();
	};
}

/**
 * Cancel active snippet generation
 */
export function cancelSnippetGeneration(): void {
	globalThis.electronAPI.cancelSnippetGeneration();
}

// Helper function to open dialog
export const openContextAwareSnippetsDialog = () => {
	const store = useContextAwareSnippetsStore.getState();
	store.reset();
	store.openDialog("component", "", "");
};
