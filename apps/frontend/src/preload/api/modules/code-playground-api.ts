import { ipcRenderer } from "electron";
import type { PlaygroundResult } from "../../../main/code-playground-service";

export interface CodePlaygroundAPI {
	/**
	 * Start code playground generation
	 */
	startCodePlayground: (
		projectId: string,
		idea: string,
		playgroundType: string,
		sandboxType: string,
	) => void;

	/**
	 * Listen for streaming output chunks
	 */
	onCodePlaygroundStreamChunk: (
		callback: (chunk: string) => void,
	) => () => void;

	/**
	 * Listen for status updates
	 */
	onCodePlaygroundStatus: (callback: (status: string) => void) => () => void;

	/**
	 * Listen for errors
	 */
	onCodePlaygroundError: (callback: (error: string) => void) => () => void;

	/**
	 * Listen for completion with result
	 */
	onCodePlaygroundComplete: (
		callback: (result: PlaygroundResult) => void,
	) => () => void;

	/**
	 * Cancel active playground generation
	 */
	cancelCodePlayground: () => void;
}

export function createCodePlaygroundAPI(): CodePlaygroundAPI {
	return {
		startCodePlayground: (
			projectId: string,
			idea: string,
			playgroundType: string,
			sandboxType: string,
		) => {
			ipcRenderer.send("code-playground:start", {
				projectId,
				idea,
				playgroundType,
				sandboxType,
			});
		},

		onCodePlaygroundStreamChunk: (callback: (chunk: string) => void) => {
			const subscription = ipcRenderer.on(
				"code-playground:stream-chunk",
				(_, chunk) => callback(chunk),
			);
			return () => subscription.removeAllListeners();
		},

		onCodePlaygroundStatus: (callback: (status: string) => void) => {
			const subscription = ipcRenderer.on(
				"code-playground:status",
				(_, status) => callback(status),
			);
			return () => subscription.removeAllListeners();
		},

		onCodePlaygroundError: (callback: (error: string) => void) => {
			const subscription = ipcRenderer.on("code-playground:error", (_, error) =>
				callback(error),
			);
			return () => subscription.removeAllListeners();
		},

		onCodePlaygroundComplete: (
			callback: (result: PlaygroundResult) => void,
		) => {
			const subscription = ipcRenderer.on(
				"code-playground:complete",
				(_, result) => callback(result),
			);
			return () => subscription.removeAllListeners();
		},

		cancelCodePlayground: () => {
			ipcRenderer.send("code-playground:cancel");
		},
	};
}
