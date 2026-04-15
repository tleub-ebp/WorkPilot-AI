/**
 * Notebook Agent API
 *
 * Renderer-side bridge to the notebook agent runner.
 */

import type { ParsedNotebook } from "../../../shared/types/notebook-agent";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface NotebookAgentRunOptions {
	projectPath: string;
}

export interface NotebookAgentResult {
	notebooks: ParsedNotebook[];
}

export interface NotebookAgentEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; notebooks?: number; issues?: number };
}

export interface NotebookAgentAPI {
	runNotebookAgentScan: (
		options: NotebookAgentRunOptions,
	) => Promise<NotebookAgentResult>;
	cancelNotebookAgentScan: () => Promise<boolean>;
	onNotebookAgentEvent: (
		callback: (event: NotebookAgentEvent) => void,
	) => () => void;
	onNotebookAgentResult: (
		callback: (result: NotebookAgentResult) => void,
	) => () => void;
	onNotebookAgentError: (callback: (error: string) => void) => () => void;
}

export const createNotebookAgentAPI = (): NotebookAgentAPI => ({
	runNotebookAgentScan: (options: NotebookAgentRunOptions) =>
		invokeIpc<NotebookAgentResult>("notebookAgent:run", options),

	cancelNotebookAgentScan: () => invokeIpc<boolean>("notebookAgent:cancel"),

	onNotebookAgentEvent: (callback) =>
		createIpcListener<[NotebookAgentEvent]>("notebook-event", (payload) =>
			callback(payload),
		),

	onNotebookAgentResult: (callback) =>
		createIpcListener<[NotebookAgentResult]>("notebook-result", (payload) =>
			callback(payload),
		),

	onNotebookAgentError: (callback) =>
		createIpcListener<[string]>("notebook-error", (payload) =>
			callback(payload),
		),
});
