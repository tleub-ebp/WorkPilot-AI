/**
 * Conflict Predictor API
 *
 * Provides API interface for Conflict Predictor functionality
 */

import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface ConflictPredictorAPI {
	runConflictPrediction: (projectId: string) => Promise<void>;
	cancelConflictPrediction: () => Promise<boolean>;
	onConflictPredictionStreamChunk: (
		callback: (chunk: string) => void,
	) => () => void;
	onConflictPredictionStatus: (
		callback: (status: string) => void,
	) => () => void;
	onConflictPredictionError: (callback: (error: string) => void) => () => void;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onConflictPredictionComplete: (callback: (result: any) => void) => () => void;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onConflictPredictionEvent: (callback: (event: any) => void) => () => void;
}

export const createConflictPredictorAPI = (): ConflictPredictorAPI => ({
	runConflictPrediction: (projectId: string) =>
		invokeIpc("run-conflict-prediction", { projectId }),

	cancelConflictPrediction: () => invokeIpc("cancel-conflict-prediction"),

	onConflictPredictionStreamChunk: (callback: (chunk: string) => void) => {
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		return createIpcListener("conflict-predictor-event", (event: any) => {
			if (event.type === "progress" && event.data.status) {
				callback(event.data.status);
			}
		});
	},

	onConflictPredictionStatus: (callback: (status: string) => void) => {
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		return createIpcListener("conflict-predictor-event", (event: any) => {
			if (event.type === "progress" && event.data.status) {
				callback(event.data.status);
			}
		});
	},

	onConflictPredictionError: (callback: (error: string) => void) => {
		return createIpcListener("conflict-predictor-error", (error: string) => {
			callback(error);
		});
	},

	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onConflictPredictionComplete: (callback: (result: any) => void) => {
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		return createIpcListener("conflict-predictor-complete", (result: any) => {
			callback(result);
		});
	},

	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onConflictPredictionEvent: (callback: (event: any) => void) => {
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		return createIpcListener("conflict-predictor-event", (event: any) => {
			callback(event);
		});
	},
});

export const conflictPredictorAPI: ConflictPredictorAPI = {
	runConflictPrediction: (projectId: string) =>
		invokeIpc("run-conflict-prediction", { projectId }),

	cancelConflictPrediction: () => invokeIpc("cancel-conflict-prediction"),

	onConflictPredictionStreamChunk: (callback: (chunk: string) => void) =>
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		createIpcListener("conflict-predictor-event", (event: any) => {
			if (event.type === "progress" && event.data.status) {
				callback(event.data.status);
			}
		}),

	onConflictPredictionStatus: (callback: (status: string) => void) =>
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		createIpcListener("conflict-predictor-event", (event: any) => {
			if (event.type === "progress" && event.data.status) {
				callback(event.data.status);
			}
		}),

	onConflictPredictionError: (callback: (error: string) => void) =>
		createIpcListener("conflict-predictor-error", (error: string) => {
			callback(error);
		}),

	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onConflictPredictionComplete: (callback: (result: any) => void) =>
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		createIpcListener("conflict-predictor-complete", (result: any) => {
			callback(result);
		}),

	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onConflictPredictionEvent: (callback: (event: any) => void) =>
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		createIpcListener("conflict-predictor-event", (event: any) => {
			callback(event);
		}),
};
