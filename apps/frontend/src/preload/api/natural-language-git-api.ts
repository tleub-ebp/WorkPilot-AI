import { ipcRenderer } from "electron";
import { invokeIpc } from "./modules/ipc-utils";

export interface NaturalLanguageGitRequest {
	projectPath: string;
	command: string;
	model?: string;
	thinkingLevel?: string;
}

interface NaturalLanguageGitResult {
	generatedCommand: string;
	explanation: string;
	executionOutput: string;
	success: boolean;
}

export interface NaturalLanguageGitAPI {
	executeNaturalLanguageGit: (
		request: NaturalLanguageGitRequest,
	) => Promise<void>;
	cancelNaturalLanguageGit: () => Promise<boolean>;
	onNaturalLanguageGitStatus: (
		callback: (status: string) => void,
	) => () => void;
	onNaturalLanguageGitStreamChunk: (
		callback: (chunk: string) => void,
	) => () => void;
	onNaturalLanguageGitError: (callback: (error: string) => void) => () => void;
	onNaturalLanguageGitComplete: (
		callback: (result: NaturalLanguageGitResult) => void,
	) => () => void;
	removeNaturalLanguageGitStatusListener: (
		callback: (status: string) => void,
	) => void;
	removeNaturalLanguageGitStreamChunkListener: (
		callback: (chunk: string) => void,
	) => void;
	removeNaturalLanguageGitErrorListener: (
		callback: (error: string) => void,
	) => void;
	removeNaturalLanguageGitCompleteListener: (
		callback: (result: NaturalLanguageGitResult) => void,
	) => void;
}

// Track handler wrappers so removeListener can find the correct ipcRenderer handler
const statusHandlerMap = new WeakMap<
	(status: string) => void,
	(_event: Electron.IpcRendererEvent, status: string) => void
>();
const chunkHandlerMap = new WeakMap<
	(chunk: string) => void,
	(_event: Electron.IpcRendererEvent, chunk: string) => void
>();
const errorHandlerMap = new WeakMap<
	(error: string) => void,
	(_event: Electron.IpcRendererEvent, error: string) => void
>();
const completeHandlerMap = new WeakMap<
	(result: NaturalLanguageGitResult) => void,
	(_event: Electron.IpcRendererEvent, result: NaturalLanguageGitResult) => void
>();

function registerStatusListener(
	callback: (status: string) => void,
): () => void {
	const handler = (_event: Electron.IpcRendererEvent, status: string) => {
		callback(status);
	};
	statusHandlerMap.set(callback, handler);
	ipcRenderer.on("natural-language-git-status", handler);
	return () => {
		ipcRenderer.removeListener("natural-language-git-status", handler);
		statusHandlerMap.delete(callback);
	};
}

function registerChunkListener(
	callback: (chunk: string) => void,
): () => void {
	const handler = (_event: Electron.IpcRendererEvent, chunk: string) => {
		callback(chunk);
	};
	chunkHandlerMap.set(callback, handler);
	ipcRenderer.on("natural-language-git-stream-chunk", handler);
	return () => {
		ipcRenderer.removeListener("natural-language-git-stream-chunk", handler);
		chunkHandlerMap.delete(callback);
	};
}

function registerErrorListener(
	callback: (error: string) => void,
): () => void {
	const handler = (_event: Electron.IpcRendererEvent, error: string) => {
		callback(error);
	};
	errorHandlerMap.set(callback, handler);
	ipcRenderer.on("natural-language-git-error", handler);
	return () => {
		ipcRenderer.removeListener("natural-language-git-error", handler);
		errorHandlerMap.delete(callback);
	};
}

function registerCompleteListener(
	callback: (result: NaturalLanguageGitResult) => void,
): () => void {
	const handler = (
		_event: Electron.IpcRendererEvent,
		result: NaturalLanguageGitResult,
	) => {
		callback(result);
	};
	completeHandlerMap.set(callback, handler);
	ipcRenderer.on("natural-language-git-complete", handler);
	return () => {
		ipcRenderer.removeListener("natural-language-git-complete", handler);
		completeHandlerMap.delete(callback);
	};
}

function removeStatusListener(callback: (status: string) => void): void {
	const handler = statusHandlerMap.get(callback);
	if (handler) {
		ipcRenderer.removeListener("natural-language-git-status", handler);
		statusHandlerMap.delete(callback);
	}
}

function removeChunkListener(callback: (chunk: string) => void): void {
	const handler = chunkHandlerMap.get(callback);
	if (handler) {
		ipcRenderer.removeListener("natural-language-git-stream-chunk", handler);
		chunkHandlerMap.delete(callback);
	}
}

function removeErrorListener(callback: (error: string) => void): void {
	const handler = errorHandlerMap.get(callback);
	if (handler) {
		ipcRenderer.removeListener("natural-language-git-error", handler);
		errorHandlerMap.delete(callback);
	}
}

function removeCompleteListener(
	callback: (result: NaturalLanguageGitResult) => void,
): void {
	const handler = completeHandlerMap.get(callback);
	if (handler) {
		ipcRenderer.removeListener("natural-language-git-complete", handler);
		completeHandlerMap.delete(callback);
	}
}

export const createNaturalLanguageGitAPI = (): NaturalLanguageGitAPI => ({
	executeNaturalLanguageGit: (request: NaturalLanguageGitRequest) =>
		invokeIpc("execute-natural-language-git", request),
	cancelNaturalLanguageGit: () => invokeIpc("cancel-natural-language-git"),
	onNaturalLanguageGitStatus: (callback: (status: string) => void) =>
		registerStatusListener(callback),
	onNaturalLanguageGitStreamChunk: (callback: (chunk: string) => void) =>
		registerChunkListener(callback),
	onNaturalLanguageGitError: (callback: (error: string) => void) =>
		registerErrorListener(callback),
	onNaturalLanguageGitComplete: (
		callback: (result: NaturalLanguageGitResult) => void,
	) => registerCompleteListener(callback),
	removeNaturalLanguageGitStatusListener: (
		callback: (status: string) => void,
	) => removeStatusListener(callback),
	removeNaturalLanguageGitStreamChunkListener: (
		callback: (chunk: string) => void,
	) => removeChunkListener(callback),
	removeNaturalLanguageGitErrorListener: (callback: (error: string) => void) =>
		removeErrorListener(callback),
	removeNaturalLanguageGitCompleteListener: (
		callback: (result: NaturalLanguageGitResult) => void,
	) => removeCompleteListener(callback),
});
