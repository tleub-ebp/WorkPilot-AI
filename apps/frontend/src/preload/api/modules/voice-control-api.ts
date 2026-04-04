/**
 * Voice Control API module for preload script
 *
 * Provides voice control functionality through IPC communication
 */

import { type IpcRendererEvent, ipcRenderer } from "electron";
import { invokeIpc } from "./ipc-utils";

export interface VoiceControlAPI {
	// Voice recording control
	startVoiceRecording: (request?: {
		projectDir?: string;
		language?: string;
		model?: string;
		thinkingLevel?: string;
	}) => Promise<{ success: boolean; error?: string }>;

	stopVoiceRecording: () => Promise<{ success: boolean; error?: string }>;
	cancelVoiceControl: () => Promise<{
		success: boolean;
		cancelled: boolean;
		error?: string;
	}>;
	isVoiceControlActive: () => Promise<{
		success: boolean;
		isActive: boolean;
		error?: string;
	}>;

	// Configuration
	configureVoiceControl: (config: {
		pythonPath?: string;
		autoBuildSourcePath?: string;
	}) => Promise<{ success: boolean; error?: string }>;

	// Event listeners
	onVoiceControlStatus: (callback: (status: string) => void) => () => void;
	onVoiceControlStreamChunk: (callback: (chunk: string) => void) => () => void;
	onVoiceControlError: (callback: (error: string) => void) => () => void;
	onVoiceControlComplete: (
		callback: (result: {
			transcript: string;
			command: string;
			action: string;
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			parameters: Record<string, any>;
			confidence: number;
		}) => void,
	) => () => void;
	onVoiceControlAudioLevel: (callback: (level: number) => void) => () => void;
	onVoiceControlDuration: (callback: (duration: number) => void) => () => void;
}

export function createVoiceControlAPI(): VoiceControlAPI {
	return {
		// Voice recording control
		startVoiceRecording: async (request) => {
			return await invokeIpc("voice-control:startRecording", request);
		},

		stopVoiceRecording: async () => {
			return await invokeIpc("voice-control:stopRecording");
		},

		cancelVoiceControl: async () => {
			return await invokeIpc("voice-control:cancel");
		},

		isVoiceControlActive: async () => {
			return await invokeIpc("voice-control:isActive");
		},

		// Configuration
		configureVoiceControl: async (config) => {
			return await invokeIpc("voice-control:configure", config);
		},

		// Event listeners
		onVoiceControlStatus: (callback) => {
			ipcRenderer.on(
				"voice-control:status",
				(_event: IpcRendererEvent, status: string) => callback(status),
			);
			return () => {
				ipcRenderer.removeAllListeners("voice-control:status");
			};
		},

		onVoiceControlStreamChunk: (callback) => {
			ipcRenderer.on(
				"voice-control:stream-chunk",
				(_event: IpcRendererEvent, chunk: string) => callback(chunk),
			);
			return () => {
				ipcRenderer.removeAllListeners("voice-control:stream-chunk");
			};
		},

		onVoiceControlError: (callback) => {
			ipcRenderer.on(
				"voice-control:error",
				(_event: IpcRendererEvent, error: string) => callback(error),
			);
			return () => {
				ipcRenderer.removeAllListeners("voice-control:error");
			};
		},

		onVoiceControlComplete: (callback) => {
			ipcRenderer.on(
				"voice-control:complete",
				(
					_event: IpcRendererEvent,
					result: {
						transcript: string;
						command: string;
						action: string;
						// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
						parameters: Record<string, any>;
						confidence: number;
					},
				) => callback(result),
			);
			return () => {
				ipcRenderer.removeAllListeners("voice-control:complete");
			};
		},

		onVoiceControlAudioLevel: (callback) => {
			ipcRenderer.on(
				"voice-control:audio-level",
				(_event: IpcRendererEvent, level: number) => callback(level),
			);
			return () => {
				ipcRenderer.removeAllListeners("voice-control:audio-level");
			};
		},

		onVoiceControlDuration: (callback) => {
			ipcRenderer.on(
				"voice-control:duration",
				(_event: IpcRendererEvent, duration: number) => callback(duration),
			);
			return () => {
				ipcRenderer.removeAllListeners("voice-control:duration");
			};
		},
	};
}
