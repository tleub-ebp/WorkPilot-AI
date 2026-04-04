/**
 * Documentation Agent API module
 */

export interface DocumentationAgentRequest {
	projectDir: string;
	docTypes?: string[];
	outputDir?: string;
	insertInline?: boolean;
	model?: string;
	thinkingLevel?: string;
}

export interface DocumentationAgentResult {
	doc_types_generated: string[];
	files_created: string[];
	outdated_docs_updated?: string[];
	coverage_before?: { overall_coverage: number };
	coverage_after?: { overall_coverage: number };
}

export interface DocumentationAgentAPI {
	generateDocumentation: (
		request: DocumentationAgentRequest,
	) => Promise<{ success: boolean; error?: string }>;
	cancelDocumentation: () => Promise<{
		success: boolean;
		cancelled: boolean;
		error?: string;
	}>;
	configureDocumentationAgent: (config: {
		pythonPath?: string;
	}) => Promise<{ success: boolean; error?: string }>;
	onDocumentationAgentStatus: (
		callback: (status: string) => void,
	) => () => void;
	onDocumentationAgentStreamChunk: (
		callback: (chunk: string) => void,
	) => () => void;
	onDocumentationAgentError: (callback: (error: string) => void) => () => void;
	onDocumentationAgentComplete: (
		callback: (result: DocumentationAgentResult) => void,
	) => () => void;
}

export function createDocumentationAgentAPI(): DocumentationAgentAPI {
	return {
		generateDocumentation: (request) =>
			globalThis.electronAPI.invoke("documentationAgent:generate", request),
		cancelDocumentation: () =>
			globalThis.electronAPI.invoke("documentationAgent:cancel"),
		configureDocumentationAgent: (config) =>
			globalThis.electronAPI.invoke("documentationAgent:configure", config),
		onDocumentationAgentStatus: (callback) =>
			globalThis.electronAPI.on("documentationAgent:status", callback),
		onDocumentationAgentStreamChunk: (callback) =>
			globalThis.electronAPI.on("documentationAgent:streamChunk", callback),
		onDocumentationAgentError: (callback) =>
			globalThis.electronAPI.on("documentationAgent:error", callback),
		onDocumentationAgentComplete: (callback) =>
			globalThis.electronAPI.on("documentationAgent:complete", callback),
	};
}
