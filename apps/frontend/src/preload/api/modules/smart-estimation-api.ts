/**
 * Smart Estimation API
 *
 * Provides API interface for Smart Estimation functionality
 */

import { invokeIpc } from "./ipc-utils";

export interface SmartEstimationAPI {
	runSmartEstimation: (
		projectId: string,
		taskDescription: string,
	) => Promise<void>;
	cancelSmartEstimation: () => Promise<boolean>;
	onSmartEstimationStreamChunk: (
		callback: (chunk: string) => void,
	) => () => void;
	onSmartEstimationStatus: (callback: (status: string) => void) => () => void;
	onSmartEstimationError: (callback: (error: string) => void) => () => void;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onSmartEstimationComplete: (callback: (result: any) => void) => () => void;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onSmartEstimationEvent: (callback: (event: any) => void) => () => void;
}

export const createSmartEstimationAPI = (): SmartEstimationAPI => ({
	runSmartEstimation: (projectId: string, taskDescription: string) =>
		invokeIpc("smart-estimation:run", { projectId, taskDescription }),

	cancelSmartEstimation: () => invokeIpc("smart-estimation:cancel"),

	onSmartEstimationStreamChunk: (_callback: (chunk: string) => void) => {
		// TODO: Implement event listener setup
		return () => {
			/* TODO: Implement cleanup */
		};
	},

	onSmartEstimationStatus: (_callback: (status: string) => void) => {
		// TODO: Implement event listener setup
		return () => {
			/* TODO: Implement cleanup */
		};
	},

	onSmartEstimationError: (_callback: (error: string) => void) => {
		// TODO: Implement event listener setup
		return () => {
			/* TODO: Implement cleanup */
		};
	},

	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onSmartEstimationComplete: (_callback: (result: any) => void) => {
		// TODO: Implement event listener setup
		return () => {
			/* TODO: Implement cleanup */
		};
	},

	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onSmartEstimationEvent: (_callback: (event: any) => void) => {
		// TODO: Implement event listener setup
		return () => {
			/* TODO: Implement cleanup */
		};
	},
});

// Note: This module exports functions that are integrated into the main ElectronAPI
// The contextBridge exposure is handled in the main preload/index.ts file
