// AUTO-GENERATED — do not edit by hand.
// Regenerate with: pnpm run generate:provider-types
// Source: config/configured_providers.json

/**
 * Canonical entry for an LLM provider as declared in
 * `config/configured_providers.json`. Both the Python backend
 * (`apps/backend/provider_api.py`) and the Electron/React frontend
 * consume this same JSON file.
 */
export interface ConfiguredProvider {
	/** Stable machine-readable identifier, used in API calls and config keys. */
	readonly name: ProviderName;
	/** Human-readable name displayed in the UI. */
	readonly label: string;
	/** Short description rendered under the provider in settings. */
	readonly description: string;
}

/** Union type of every provider ID declared in the JSON. */
export type ProviderName =
	| "anthropic"
	| "copilot"
	| "openai"
	| "google"
	| "meta"
	| "mistral"
	| "grok"
	| "windsurf"
	| "ollama"
	| "aws";

/** Every provider, frozen so callers cannot mutate the canonical list. */
export const CONFIGURED_PROVIDERS: readonly ConfiguredProvider[] = Object.freeze([
	{ name: "anthropic", label: "Anthropic (Claude)", description: "Claude, focalisé sur la sécurité et l’IA d’entreprise." },
	{ name: "copilot", label: "GitHub Copilot", description: "Assistant de code IA par GitHub, basé sur les modèles OpenAI et Claude." },
	{ name: "openai", label: "OpenAI", description: "Créateur de la série GPT (ChatGPT, GPT-4/4o/5)." },
	{ name: "google", label: "Google / Google DeepMind", description: "Modèles Gemini." },
	{ name: "meta", label: "Meta (Facebook/Meta AI)", description: "Modèles LLaMA et variantes open source." },
	{ name: "mistral", label: "Mistral AI", description: "Startup française, LLM open weight et commercial." },
	{ name: "grok", label: "Grok (xAI)", description: "Modèles Grok via xAI, la société d’Elon Musk." },
	{ name: "windsurf", label: "Windsurf AI", description: "Provider Windsurf pour l’utilisation des tokens Windsurf." },
	{ name: "ollama", label: "LLM local (Ollama, LM Studio, etc.)", description: "Exécutez un modèle LLM localement sur votre machine (Ollama, LM Studio, etc.)." },
	{ name: "aws", label: "Amazon Web Services (AWS)", description: "Offre des API LLM intégrées à ses services cloud." },
]);

/** `Set` of provider IDs — constant-time membership check. */
export const PROVIDER_NAMES: ReadonlySet<ProviderName> = new Set(
	CONFIGURED_PROVIDERS.map((p) => p.name),
);

/** Type guard — narrows an arbitrary string to `ProviderName`. */
export function isProviderName(value: string): value is ProviderName {
	return (PROVIDER_NAMES as ReadonlySet<string>).has(value);
}
