// Types unifiés pour la gestion multi-connecteur
export type LLMProvider =
	| "claude"
	| "copilot"
	| "openai"
	| "mistral"
	| "grok"
	| "gemini"
	| "ollama"
	| "AWS"
	| "windsurf"
	| "cursor"
	| string;

export interface MultiConnectorAccount {
	id: string;
	provider: LLMProvider;
	name: string;
	apiKey?: string;
	baseUrl?: string;
	email?: string;
	status: "connected" | "disconnected" | "error" | "pending";
	isActive: boolean;
	createdAt?: number;
	updatedAt?: number;
}

export interface MultiConnectorProvider {
	provider: LLMProvider;
	label: string;
	logoUrl?: string;
	accounts: MultiConnectorAccount[];
	canAddMultiple: boolean;
	docUrl?: string;
}
