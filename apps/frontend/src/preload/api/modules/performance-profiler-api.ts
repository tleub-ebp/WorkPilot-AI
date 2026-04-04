/**
 * Performance Profiler Agent API module
 */

export interface PerformanceProfilerRequest {
	projectDir: string;
	autoImplement?: boolean;
	model?: string;
	thinkingLevel?: string;
}

export interface PerformanceProfilerResult {
	bottlenecks: Array<{
		description: string;
		severity: string;
		bottleneck_type: string;
		file_path?: string;
		line_number?: number;
	}>;
	benchmarks: Array<{ name: string; duration_ms?: number; error?: string }>;
	suggestions: Array<{
		title: string;
		description: string;
		effort: string;
		estimated_improvement?: string;
		implementation?: string;
	}>;
	summary: { total_bottlenecks: number; suggestions_count: number };
}

export interface PerformanceProfilerAPI {
	startPerformanceProfiling: (
		request: PerformanceProfilerRequest,
	) => Promise<{ success: boolean; error?: string }>;
	cancelPerformanceProfiling: () => Promise<{
		success: boolean;
		cancelled: boolean;
		error?: string;
	}>;
	configurePerformanceProfiler: (config: {
		pythonPath?: string;
	}) => Promise<{ success: boolean; error?: string }>;
	onPerformanceProfilerStatus: (
		callback: (status: string) => void,
	) => () => void;
	onPerformanceProfilerStreamChunk: (
		callback: (chunk: string) => void,
	) => () => void;
	onPerformanceProfilerError: (callback: (error: string) => void) => () => void;
	onPerformanceProfilerComplete: (
		callback: (result: PerformanceProfilerResult) => void,
	) => () => void;
	onPerformanceProfilerImplementationComplete: (
		callback: (result: unknown) => void,
	) => () => void;
}

export function createPerformanceProfilerAPI(): PerformanceProfilerAPI {
	return {
		startPerformanceProfiling: (request) =>
			globalThis.electronAPI.invoke("performanceProfiler:start", request),
		cancelPerformanceProfiling: () =>
			globalThis.electronAPI.invoke("performanceProfiler:cancel"),
		configurePerformanceProfiler: (config) =>
			globalThis.electronAPI.invoke("performanceProfiler:configure", config),
		onPerformanceProfilerStatus: (callback) =>
			globalThis.electronAPI.on("performanceProfiler:status", callback),
		onPerformanceProfilerStreamChunk: (callback) =>
			globalThis.electronAPI.on("performanceProfiler:streamChunk", callback),
		onPerformanceProfilerError: (callback) =>
			globalThis.electronAPI.on("performanceProfiler:error", callback),
		onPerformanceProfilerComplete: (callback) =>
			globalThis.electronAPI.on("performanceProfiler:complete", callback),
		onPerformanceProfilerImplementationComplete: (callback) =>
			globalThis.electronAPI.on(
				"performanceProfiler:implementationComplete",
				callback,
			),
	};
}
