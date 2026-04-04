/**
 * Plugin Marketplace Types
 *
 * Types for the Plugin Marketplace — community-driven ecosystem for
 * extending WorkPilot AI with agents, integrations, templates, themes, and prompts.
 */

/** Plugin type categories */
export type PluginType =
	| "agent"
	| "integration"
	| "spec-template"
	| "theme"
	| "custom-prompt";

/** Plugin sort options */
export type PluginSortBy = "popular" | "rating" | "newest" | "name";

/** Active tab in the marketplace */
export type PluginMarketplaceTab = "catalog" | "installed" | "sdk";

/**
 * A plugin entry in the marketplace catalog.
 */
export interface MarketplacePlugin {
	id: string;
	name: string;
	tagline: string;
	description: string;
	author: string;
	authorVerified: boolean;
	type: PluginType;
	icon: string;
	color: string;
	version: string;
	downloads: number;
	rating: number;
	ratingCount: number;
	verified: boolean;
	tags: string[];
	repositoryUrl?: string;
	homepageUrl?: string;
	/** For theme plugins: CSS variable overrides */
	themeData?: Record<string, string>;
	/** For spec-template plugins: template content */
	templateContent?: string;
	/** For custom-prompt plugins: prompt content */
	promptContent?: string;
	/** For agent plugins: agent config */
	agentConfig?: PluginAgentConfig;
	/** For integration plugins: integration config */
	integrationConfig?: PluginIntegrationConfig;
	addedAt: string;
	updatedAt: string;
}

/** Agent plugin configuration */
export interface PluginAgentConfig {
	systemPrompt: string;
	model?: string;
	tools?: string[];
	triggerKeywords?: string[];
}

/** Integration plugin configuration */
export interface PluginIntegrationConfig {
	webhookUrl?: string;
	apiEndpoint?: string;
	authType: "none" | "apikey" | "oauth" | "basic";
	requiredEnvVars?: Array<{
		name: string;
		label: string;
		description: string;
		secret: boolean;
	}>;
}

/** An installed plugin instance */
export interface InstalledPlugin {
	pluginId: string;
	name: string;
	version: string;
	type: PluginType;
	enabled: boolean;
	installedAt: string;
	config?: Record<string, string>;
}

/** Filter options for the marketplace catalog */
export interface PluginMarketplaceFilters {
	search: string;
	type: PluginType | "all";
	sortBy: PluginSortBy;
	showInstalledOnly: boolean;
	showVerifiedOnly: boolean;
}
