export type ApiProviderPreset = {
	id: string;
	baseUrl: string;
	labelKey: string;
};

export const API_PROVIDER_PRESETS: readonly ApiProviderPreset[] = [
	{
		id: "anthropic",
		baseUrl: "https://api.anthropic.com",
		labelKey: "settings:apiProfiles.presets.anthropic",
	},
	{
		id: "openai",
		baseUrl: "https://api.openai.com/v1",
		labelKey: "settings:apiProfiles.presets.openai",
	},
	{
		id: "mistral",
		baseUrl: "https://api.mistral.ai/v1",
		labelKey: "settings:apiProfiles.presets.mistral",
	},
	{
		id: "grok",
		baseUrl: "https://api.grok.x.ai/v1",
		labelKey: "settings:apiProfiles.presets.grok",
	},
	{
		id: "gemini",
		baseUrl: "https://generativelanguage.googleapis.com/v1beta",
		labelKey: "settings:apiProfiles.presets.gemini",
	},
	{
		id: "cohere",
		baseUrl: "https://api.cohere.ai/v1",
		labelKey: "settings:apiProfiles.presets.cohere",
	},
	{
		id: "openrouter",
		baseUrl: "https://openrouter.ai/api",
		labelKey: "settings:apiProfiles.presets.openrouter",
	},
	{
		id: "groq",
		baseUrl: "https://api.groq.com/openai/v1",
		labelKey: "settings:apiProfiles.presets.groq",
	},
	{
		id: "ollama",
		baseUrl: "http://localhost:11434/v1",
		labelKey: "settings:apiProfiles.presets.ollama",
	},
	{
		id: "windsurf",
		baseUrl: "https://server.codeium.com/api/v1",
		labelKey: "settings:apiProfiles.presets.windsurf",
	},
];
