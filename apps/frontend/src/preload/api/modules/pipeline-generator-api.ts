/**
 * Pipeline Generator API module
 */

import type {
	CiPlatform,
	PipelineGeneratorRequest,
	PipelineGeneratorResult,
} from "../../../main/pipeline-generator-service";
import {
	createIpcListener,
	type IpcListenerCleanup,
	invokeIpc,
} from "./ipc-utils";

export type { CiPlatform, PipelineGeneratorRequest, PipelineGeneratorResult };

export interface PipelineGeneratorAPI {
	generatePipelines: (
		request: PipelineGeneratorRequest,
	) => Promise<{ success: boolean; error?: string }>;
	cancelPipelineGeneration: () => Promise<{
		success: boolean;
		cancelled: boolean;
		error?: string;
	}>;
	configurePipelineGenerator: (config: {
		pythonPath?: string;
		autoBuildSourcePath?: string;
	}) => Promise<{ success: boolean; error?: string }>;
	onPipelineGeneratorStatus: (
		callback: (status: string) => void,
	) => IpcListenerCleanup;
	onPipelineGeneratorStreamChunk: (
		callback: (chunk: string) => void,
	) => IpcListenerCleanup;
	onPipelineGeneratorError: (
		callback: (error: string) => void,
	) => IpcListenerCleanup;
	onPipelineGeneratorComplete: (
		callback: (result: PipelineGeneratorResult) => void,
	) => IpcListenerCleanup;
}

export function createPipelineGeneratorAPI(): PipelineGeneratorAPI {
	return {
		generatePipelines: (request) =>
			invokeIpc<{ success: boolean; error?: string }>(
				"pipelineGenerator:generate",
				request,
			),
		cancelPipelineGeneration: () =>
			invokeIpc<{ success: boolean; cancelled: boolean; error?: string }>(
				"pipelineGenerator:cancel",
			),
		configurePipelineGenerator: (config) =>
			invokeIpc<{ success: boolean; error?: string }>(
				"pipelineGenerator:configure",
				config,
			),
		onPipelineGeneratorStatus: (callback) =>
			createIpcListener<[string]>("pipelineGenerator:status", callback),
		onPipelineGeneratorStreamChunk: (callback) =>
			createIpcListener<[string]>("pipelineGenerator:streamChunk", callback),
		onPipelineGeneratorError: (callback) =>
			createIpcListener<[string]>("pipelineGenerator:error", callback),
		onPipelineGeneratorComplete: (callback) =>
			createIpcListener<[PipelineGeneratorResult]>(
				"pipelineGenerator:complete",
				callback,
			),
	};
}
