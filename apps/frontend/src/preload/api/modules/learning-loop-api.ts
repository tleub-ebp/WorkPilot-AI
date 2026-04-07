/**
 * Learning Loop API module
 *
 * Provides API methods for interacting with the Autonomous Agent Learning Loop.
 * Uses ipcRenderer utilities directly (not window.electronAPI) since this runs in a preload context.
 */

import type * as LearningLoopTypes from "../../../shared/types/learning-loop";
import { createIpcListener, invokeIpc, sendIpc } from "./ipc-utils";

export interface LearningLoopAPI {
	// Operations
	getLearningPatterns: (projectId: string) => Promise<{
		success: boolean;
		data?: LearningLoopTypes.LearningPattern[];
		error?: string;
	}>;
	getLearningSummary: (projectId: string) => Promise<{
		success: boolean;
		data?: LearningLoopTypes.LearningSummary;
		error?: string;
	}>;
	runLearningAnalysis: (projectId: string, specId?: string) => void;
	stopLearningAnalysis: () => Promise<{
		success: boolean;
		cancelled: boolean;
		error?: string;
	}>;
	deleteLearningPattern: (
		projectId: string,
		patternId: string,
	) => Promise<{ success: boolean; error?: string }>;
	toggleLearningPattern: (
		projectId: string,
		patternId: string,
	) => Promise<{ success: boolean; data?: boolean; error?: string }>;

	// Event listeners
	onLearningLoopStatus: (callback: (status: string) => void) => () => void;
	onLearningLoopStreamChunk: (callback: (chunk: string) => void) => () => void;
	onLearningLoopError: (callback: (error: string) => void) => () => void;
	onLearningLoopComplete: (
		callback: (result: LearningLoopTypes.LearningLoopCompleteResult) => void,
	) => () => void;
}

/**
 * Create the Learning Loop API object
 */
export function createLearningLoopAPI(): LearningLoopAPI {
	return {
		// Operations
		getLearningPatterns: (projectId: string) =>
			invokeIpc("learningLoop:getPatterns", projectId),

		getLearningSummary: (projectId: string) =>
			invokeIpc("learningLoop:getSummary", projectId),

		runLearningAnalysis: (projectId: string, specId?: string) =>
			sendIpc("learningLoop:runAnalysis", projectId, specId),

		stopLearningAnalysis: () => invokeIpc("learningLoop:stopAnalysis"),

		deleteLearningPattern: (projectId: string, patternId: string) =>
			invokeIpc("learningLoop:deletePattern", projectId, patternId),

		toggleLearningPattern: (projectId: string, patternId: string) =>
			invokeIpc("learningLoop:togglePattern", projectId, patternId),

		// Event listeners
		onLearningLoopStatus: (callback: (status: string) => void) =>
			createIpcListener<[string]>("learningLoop:status", callback),

		onLearningLoopStreamChunk: (callback: (chunk: string) => void) =>
			createIpcListener<[string]>("learningLoop:streamChunk", callback),

		onLearningLoopError: (callback: (error: string) => void) =>
			createIpcListener<[string]>("learningLoop:error", callback),

		onLearningLoopComplete: (
			callback: (result: LearningLoopTypes.LearningLoopCompleteResult) => void,
		) =>
			createIpcListener<[LearningLoopTypes.LearningLoopCompleteResult]>(
				"learningLoop:complete",
				callback,
			),
	};
}
