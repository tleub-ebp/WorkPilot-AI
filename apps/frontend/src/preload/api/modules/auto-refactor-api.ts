/**
 * Auto-Refactor API module
 *
 * Provides API methods for interacting with the Auto-Refactor Agent functionality
 */

export interface AutoRefactorRequest {
	projectDir: string;
	model?: string;
	thinkingLevel?: string;
	autoExecute?: boolean;
}

export interface AutoRefactorResult {
	analysis: {
		status: string;
		analysis: unknown;
		files_analyzed: number;
	};
	plan: {
		status: string;
		plan: unknown;
	};
	execution: {
		status: string;
		execution: unknown;
		auto_executed: boolean;
	};
	summary: {
		issues_found: number;
		files_analyzed: number;
		refactoring_items: number;
		quick_wins: number;
		estimated_effort: string;
		risk_level: string;
	};
}

export interface AutoRefactorAPI {
	// Methods
	startAutoRefactor: (
		request: AutoRefactorRequest,
	) => Promise<{ success: boolean; error?: string }>;
	cancelAutoRefactor: () => Promise<{
		success: boolean;
		cancelled: boolean;
		error?: string;
	}>;
	configureAutoRefactor: (config: {
		pythonPath?: string;
		autoBuildSourcePath?: string;
	}) => Promise<{ success: boolean; error?: string }>;

	// Event listeners
	onAutoRefactorStatus: (callback: (status: string) => void) => () => void;
	onAutoRefactorStreamChunk: (callback: (chunk: string) => void) => () => void;
	onAutoRefactorError: (callback: (error: string) => void) => () => void;
	onAutoRefactorComplete: (
		callback: (result: AutoRefactorResult) => void,
	) => () => void;
	onAutoRefactorExecutionComplete: (
		callback: (result: unknown) => void,
	) => () => void;
}

/**
 * Create the Auto-Refactor API object
 */
export function createAutoRefactorAPI(): AutoRefactorAPI {
	return {
		// Methods
		startAutoRefactor: (request: AutoRefactorRequest) =>
			window.electronAPI.invoke("auto-refactor:start", request),

		cancelAutoRefactor: () => window.electronAPI.invoke("auto-refactor:cancel"),

		configureAutoRefactor: (config: {
			pythonPath?: string;
			autoBuildSourcePath?: string;
		}) => window.electronAPI.invoke("auto-refactor:configure", config),

		// Event listeners
		onAutoRefactorStatus: (callback: (status: string) => void) =>
			window.electronAPI.on("auto-refactor:status", callback),

		onAutoRefactorStreamChunk: (callback: (chunk: string) => void) =>
			window.electronAPI.on("auto-refactor:stream-chunk", callback),

		onAutoRefactorError: (callback: (error: string) => void) =>
			window.electronAPI.on("auto-refactor:error", callback),

		onAutoRefactorComplete: (callback: (result: AutoRefactorResult) => void) =>
			window.electronAPI.on("auto-refactor:complete", callback),

		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		onAutoRefactorExecutionComplete: (callback: (result: any) => void) =>
			window.electronAPI.on("auto-refactor:execution-complete", callback),
	};
}
