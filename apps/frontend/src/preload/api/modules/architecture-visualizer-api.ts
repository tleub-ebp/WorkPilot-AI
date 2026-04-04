/**
 * Architecture Visualizer API module
 */

export interface ArchitectureVisualizerRequest {
	projectDir: string;
	diagramTypes?: string[];
	outputDir?: string;
	model?: string;
	thinkingLevel?: string;
}

export interface ArchitectureVisualizerResult {
	project_dir: string;
	diagram_types_analyzed: string[];
	diagrams: Record<
		string,
		{
			title: string;
			mermaid_code: string;
			nodes?: unknown[];
			edges?: unknown[];
		}
	>;
	output_dir: string;
	summary: { total_diagrams: number; total_nodes: number; total_edges: number };
}

export interface ArchitectureVisualizerAPI {
	generateArchitectureDiagrams: (
		request: ArchitectureVisualizerRequest,
	) => Promise<{ success: boolean; error?: string }>;
	cancelArchitectureVisualization: () => Promise<{
		success: boolean;
		cancelled: boolean;
		error?: string;
	}>;
	configureArchitectureVisualizer: (config: {
		pythonPath?: string;
	}) => Promise<{ success: boolean; error?: string }>;
	onArchitectureVisualizerStatus: (
		callback: (status: string) => void,
	) => () => void;
	onArchitectureVisualizerStreamChunk: (
		callback: (chunk: string) => void,
	) => () => void;
	onArchitectureVisualizerError: (
		callback: (error: string) => void,
	) => () => void;
	onArchitectureVisualizerComplete: (
		callback: (result: ArchitectureVisualizerResult) => void,
	) => () => void;
}

export function createArchitectureVisualizerAPI(): ArchitectureVisualizerAPI {
	return {
		generateArchitectureDiagrams: (request) =>
			globalThis.electronAPI.invoke("architectureVisualizer:generate", request),
		cancelArchitectureVisualization: () =>
			globalThis.electronAPI.invoke("architectureVisualizer:cancel"),
		configureArchitectureVisualizer: (config) =>
			globalThis.electronAPI.invoke("architectureVisualizer:configure", config),
		onArchitectureVisualizerStatus: (callback) =>
			globalThis.electronAPI.on("architectureVisualizer:status", callback),
		onArchitectureVisualizerStreamChunk: (callback) =>
			globalThis.electronAPI.on("architectureVisualizer:streamChunk", callback),
		onArchitectureVisualizerError: (callback) =>
			globalThis.electronAPI.on("architectureVisualizer:error", callback),
		onArchitectureVisualizerComplete: (callback) =>
			globalThis.electronAPI.on("architectureVisualizer:complete", callback),
	};
}
