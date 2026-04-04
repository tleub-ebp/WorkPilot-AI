import { create } from "zustand";
import type { CodeMigrationResult } from "../../main/code-migration-service";

export type CodeMigrationPhase =
	| "idle"
	| "analyzing"
	| "planning"
	| "executing"
	| "validating"
	| "complete"
	| "error";

interface TaskProgress {
	current: number;
	total: number;
	file: string;
}

interface CodeMigrationState {
	phase: CodeMigrationPhase;
	status: string;
	streamingOutput: string;
	result: CodeMigrationResult | null;
	error: string | null;
	isOpen: boolean;
	migrationDescription: string;
	dryRun: boolean;
	taskProgress: TaskProgress | null;
	model?: string;
	thinkingLevel?: string;

	openDashboard: () => void;
	closeDashboard: () => void;
	setPhase: (phase: CodeMigrationPhase) => void;
	setStatus: (status: string) => void;
	appendStreamingOutput: (chunk: string) => void;
	setResult: (result: CodeMigrationResult) => void;
	setError: (error: string) => void;
	setMigrationDescription: (desc: string) => void;
	setDryRun: (dryRun: boolean) => void;
	setTaskProgress: (progress: TaskProgress) => void;
	setModel: (model?: string) => void;
	setThinkingLevel: (level?: string) => void;
	reset: () => void;
}

const initialState = {
	phase: "idle" as CodeMigrationPhase,
	status: "",
	streamingOutput: "",
	result: null,
	error: null,
	isOpen: false,
	migrationDescription: "",
	dryRun: true,
	taskProgress: null,
	model: undefined,
	thinkingLevel: undefined,
};

export const useCodeMigrationStore = create<CodeMigrationState>((set) => ({
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
	setMigrationDescription: (migrationDescription) =>
		set({ migrationDescription }),
	setDryRun: (dryRun) => set({ dryRun }),
	setTaskProgress: (taskProgress) => set({ taskProgress }),
	setModel: (model) => set({ model }),
	setThinkingLevel: (thinkingLevel) => set({ thinkingLevel }),
	reset: () => set(initialState),
}));

export function startCodeMigration(projectDir: string): void {
	const store = useCodeMigrationStore.getState();
	if (!store.migrationDescription.trim()) return;

	store.setPhase("analyzing");
	useCodeMigrationStore.setState({
		streamingOutput: "",
		error: null,
		result: null,
		taskProgress: null,
	});

	window.electronAPI.startCodeMigration({
		projectDir,
		migrationDescription: store.migrationDescription,
		model: store.model,
		thinkingLevel: store.thinkingLevel,
		dryRun: store.dryRun,
	});
}

export function cancelCodeMigration(): void {
	window.electronAPI.cancelCodeMigration();
	useCodeMigrationStore.getState().setPhase("idle");
}

export function setupCodeMigrationListeners(): () => void {
	const store = () => useCodeMigrationStore.getState();

	const unsubChunk = window.electronAPI.onCodeMigrationStreamChunk(
		(chunk: string) => {
			store().appendStreamingOutput(chunk);
		},
	);

	const unsubStatus = window.electronAPI.onCodeMigrationStatus(
		(status: string) => {
			store().setStatus(status);
			if (
				status.toLowerCase().includes("phase 1") ||
				status.toLowerCase().includes("analyz")
			) {
				store().setPhase("analyzing");
			} else if (
				status.toLowerCase().includes("phase 2") ||
				status.toLowerCase().includes("plan")
			) {
				store().setPhase("planning");
			} else if (
				status.toLowerCase().includes("phase 3") ||
				status.toLowerCase().includes("execut")
			) {
				store().setPhase("executing");
			} else if (status.toLowerCase().includes("validat")) {
				store().setPhase("validating");
			}
		},
	);

	const unsubError = window.electronAPI.onCodeMigrationError(
		(error: string) => {
			store().setError(error);
		},
	);

	const unsubComplete = window.electronAPI.onCodeMigrationComplete(
		(result: CodeMigrationResult) => {
			store().setResult(result);
		},
	);

	const unsubProgress = window.electronAPI.onCodeMigrationTaskProgress(
		(progress: TaskProgress) => {
			store().setTaskProgress(progress);
		},
	);

	return () => {
		unsubChunk();
		unsubStatus();
		unsubError();
		unsubComplete();
		unsubProgress();
	};
}
