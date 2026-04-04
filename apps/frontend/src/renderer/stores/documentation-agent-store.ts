import { create } from "zustand";
import type { DocumentationAgentResult } from "../../main/documentation-agent-service";

export type DocumentationAgentPhase =
	| "idle"
	| "analyzing"
	| "generating"
	| "updating"
	| "complete"
	| "error";

export const AVAILABLE_DOC_TYPES = [
	"readme",
	"api",
	"contribution",
	"docstrings",
	"diagrams",
] as const;

export type DocTypeKey = (typeof AVAILABLE_DOC_TYPES)[number];

interface DocumentationAgentState {
	phase: DocumentationAgentPhase;
	status: string;
	streamingOutput: string;
	result: DocumentationAgentResult | null;
	error: string | null;
	isOpen: boolean;
	selectedDocTypes: DocTypeKey[];
	insertInline: boolean;
	outputDir: string;
	model?: string;
	thinkingLevel?: string;

	openDashboard: () => void;
	closeDashboard: () => void;
	setPhase: (phase: DocumentationAgentPhase) => void;
	setStatus: (status: string) => void;
	appendStreamingOutput: (chunk: string) => void;
	setResult: (result: DocumentationAgentResult) => void;
	setError: (error: string) => void;
	toggleDocType: (type: DocTypeKey) => void;
	setSelectedDocTypes: (types: DocTypeKey[]) => void;
	setInsertInline: (value: boolean) => void;
	setOutputDir: (dir: string) => void;
	setModel: (model?: string) => void;
	setThinkingLevel: (level?: string) => void;
	reset: () => void;
}

const initialState = {
	phase: "idle" as DocumentationAgentPhase,
	status: "",
	streamingOutput: "",
	result: null,
	error: null,
	isOpen: false,
	selectedDocTypes: [...AVAILABLE_DOC_TYPES] as DocTypeKey[],
	insertInline: false,
	outputDir: "",
	model: undefined,
	thinkingLevel: undefined,
};

export const useDocumentationAgentStore = create<DocumentationAgentState>(
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
		setError: (error) => set({ error, phase: "error" }),
		toggleDocType: (type) =>
			set((s) => ({
				selectedDocTypes: s.selectedDocTypes.includes(type)
					? s.selectedDocTypes.filter((t) => t !== type)
					: [...s.selectedDocTypes, type],
			})),
		setSelectedDocTypes: (selectedDocTypes) => set({ selectedDocTypes }),
		setInsertInline: (insertInline) => set({ insertInline }),
		setOutputDir: (outputDir) => set({ outputDir }),
		setModel: (model) => set({ model }),
		setThinkingLevel: (thinkingLevel) => set({ thinkingLevel }),
		reset: () => set(initialState),
	}),
);

export function generateDocumentation(projectDir: string): void {
	const store = useDocumentationAgentStore.getState();
	store.setPhase("analyzing");
	useDocumentationAgentStore.setState({
		streamingOutput: "",
		error: null,
		result: null,
	});

	window.electronAPI.generateDocumentation({
		projectDir,
		docTypes: store.selectedDocTypes,
		outputDir: store.outputDir || undefined,
		insertInline: store.insertInline,
		model: store.model,
		thinkingLevel: store.thinkingLevel,
	});
}

export function cancelDocumentation(): void {
	window.electronAPI.cancelDocumentation();
	useDocumentationAgentStore.getState().setPhase("idle");
}

export function setupDocumentationAgentListeners(): () => void {
	const store = () => useDocumentationAgentStore.getState();

	const unsubChunk = window.electronAPI.onDocumentationAgentStreamChunk(
		(chunk: string) => {
			store().appendStreamingOutput(chunk);
		},
	);

	const unsubStatus = window.electronAPI.onDocumentationAgentStatus(
		(status: string) => {
			store().setStatus(status);
			if (
				status.toLowerCase().includes("phase 1") ||
				status.toLowerCase().includes("analyz")
			) {
				store().setPhase("analyzing");
			} else if (
				status.toLowerCase().includes("phase 2") ||
				status.toLowerCase().includes("generat")
			) {
				store().setPhase("generating");
			} else if (
				status.toLowerCase().includes("phase 3") ||
				status.toLowerCase().includes("updat")
			) {
				store().setPhase("updating");
			}
		},
	);

	const unsubError = window.electronAPI.onDocumentationAgentError(
		(error: string) => {
			store().setError(error);
		},
	);

	const unsubComplete = window.electronAPI.onDocumentationAgentComplete(
		(result: DocumentationAgentResult) => {
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
