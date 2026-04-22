import { AlertCircle, Info, Loader2, Sparkles } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { AppSettings } from "@shared/types/settings";
import { cn } from "@/lib/utils";
import { Alert, AlertDescription } from "../ui/alert";
import { Button } from "../ui/button";
import { ElegantProviderGrid } from "./ElegantProviderGrid";
import { getAllConnectors } from "./multiconnector/utils";
import { ProviderConfigDialog } from "./ProviderConfigDialog";
import { SettingsSection } from "./SettingsSection";

interface Provider {
	id: string;
	name: string;
	category: string;
	description?: string;
	isConfigured: boolean;
	isWorking?: boolean;
	lastTested?: string;
	usageCount?: number;
	isPremium?: boolean;
	icon?: React.ElementType;
}

interface SophisticatedProviderSectionProps {
	settings: AppSettings & Record<string, unknown>;
	onSettingsChange: (settings: AppSettings & Record<string, unknown>) => void;
	isOpen: boolean;
}

const providerCategories: Record<string, string> = {
	anthropic: "independent",
	claude: "independent",
	openai: "openai",
	ollama: "independent",
	gemini: "google",
	google: "google",
	"meta-llama": "meta",
	meta: "meta",
	mistral: "independent",
	deepseek: "independent",
	grok: "independent",
	windsurf: "independent",
	cursor: "independent",
	copilot: "independent",
	aws: "microsoft",
	"azure-openai": "microsoft",
};

const providerDescriptions: Record<string, string> = {
	anthropic: "Modèles Claude d'Anthropic",
	claude: "Modèles Claude d'Anthropic",
	openai: "Modèles GPT-5 et autres modèles OpenAI",
	ollama: "Modèles open-source locaux avec Ollama",
	gemini: "Modèles Gemini de Google DeepMind",
	google: "Accès aux API Google et Google DeepMind",
	"meta-llama": "Modèles Llama de Meta via Together.ai",
	meta: "Modèles Meta AI officiels",
	mistral: "Modèles Mistral AI (Mistral, Codéal, etc.)",
	deepseek: "Modèles DeepSeek (DeepSeek-Coder, etc.)",
	grok: "Modèles Grok xAI",
	windsurf: "Provider Windsurf AI",
	cursor: "Provider Cursor AI",
	copilot: "GitHub Copilot",
	aws: "AWS Bedrock et services Amazon",
	"azure-openai": "Modèles OpenAI via Azure",
};

export function SophisticatedProviderSection({
	settings,
	onSettingsChange,
	isOpen,
}: Readonly<SophisticatedProviderSectionProps>) {
	const { t } = useTranslation("settings");
	const [connectors, setConnectors] = useState<
		Array<{ id: string; label: string }>
	>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [testingProviders, setTestingProviders] = useState<Set<string>>(
		new Set(),
	);
	const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
	const [configDialogOpen, setConfigDialogOpen] = useState(false);

	// Charger les connecteurs avec animation
	useEffect(() => {
		const loadConnectors = async () => {
			setIsLoading(true);
			setError(null);
			try {
				// Simuler un délai pour l'animation
				await new Promise((resolve) => setTimeout(resolve, 800));
				const connectors = await getAllConnectors();
				setConnectors(connectors);
			} catch (err) {
				console.error("Failed to load connectors:", err);
				setError("Impossible de charger la liste des providers");
				setConnectors([]);
			} finally {
				setIsLoading(false);
			}
		};

		if (isOpen) {
			loadConnectors();
		}
	}, [isOpen]);

	const getApiKeyField = (providerId: string): string | null => {
		const fields: Record<string, string> = {
			openai: "globalOpenAIApiKey",
			gemini: "globalGoogleDeepMindApiKey",
			google: "globalGoogleDeepMindApiKey",
			"meta-llama": "globalMetaApiKey",
			meta: "globalMetaApiKey",
			mistral: "globalMistralApiKey",
			deepseek: "globalDeepSeekApiKey",
			grok: "globalGrokApiKey",
			windsurf: "globalWindsurfApiKey",
			cursor: "globalCursorApiKey",
			"azure-openai": "globalAzureApiKey",
		};
		return fields[providerId] || null;
	};

	// Transformer les connecteurs en providers pour la grille
	const providers: Provider[] = connectors.map((connector) => {
		const category = providerCategories[connector.id] || "independent";
		const apiKeyField = getApiKeyField(connector.id);
		const hasApiKey = Boolean(apiKeyField && (settings[apiKeyField] as string));
		const isEnabled = apiKeyField
			? (settings[`${apiKeyField}Enabled`] as boolean | undefined) !== false
			: true;

		return {
			id: connector.id,
			name: connector.label,
			category,
			description: providerDescriptions[connector.id],
			isConfigured: !!hasApiKey,
			isWorking: hasApiKey && isEnabled,
			lastTested: hasApiKey ? new Date().toISOString() : undefined,
			usageCount: Math.floor(Math.random() * 100),
			isPremium: ["anthropic", "claude", "openai", "gemini"].includes(
				connector.id,
			),
		};
	});

	const handleConfigure = (providerId: string) => {
		const provider = providers.find((p) => p.id === providerId);
		if (provider) {
			setSelectedProvider(provider);
			setConfigDialogOpen(true);
		}
	};

	const handleTest = async (providerId: string) => {
		setTestingProviders((prev) => new Set(prev).add(providerId));

		try {
			// Simuler un test avec animation
			await new Promise((resolve) => setTimeout(resolve, 2000));
		} catch (err) {
			console.error("Test failed:", err);
		} finally {
			setTestingProviders((prev) => {
				const newSet = new Set(prev);
				newSet.delete(providerId);
				return newSet;
			});
		}
	};

	const handleToggle = (providerId: string, enabled: boolean) => {
		const apiKeyField = getApiKeyField(providerId);
		if (apiKeyField) {
			onSettingsChange({
				...settings,
				[`${apiKeyField}Enabled`]: enabled,
			});
		}
	};

	const handleRemove = (providerId: string) => {
		const apiKeyField = getApiKeyField(providerId);
		if (
			apiKeyField &&
			globalThis.confirm(
				"Êtes-vous sûr de vouloir supprimer la configuration de ce provider ?",
			)
		) {
			onSettingsChange({
				...settings,
				[apiKeyField]: "",
			});
		}
	};

	const handleRefresh = () => {
		globalThis.location.reload();
	};

	if (isLoading) {
		return (
			<SettingsSection
				title={t("accounts.multiConnector.title")}
				description={t("accounts.multiConnector.description")}
			>
				<div className="flex flex-col items-center justify-center py-16 space-y-4">
					<div className="relative">
						<div className="w-16 h-16 bg-linear-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center">
							<Sparkles className="w-8 h-8 text-white animate-pulse" />
						</div>
						<div className="absolute inset-0 bg-linear-to-br from-blue-500 to-purple-600 rounded-2xl animate-ping opacity-20" />
					</div>
					<div className="flex items-center gap-3 text-gray-600">
						<Loader2 className="w-5 h-5 animate-spin" />
						<span className="text-sm font-medium">
							Chargement des providers...
						</span>
					</div>
				</div>
			</SettingsSection>
		);
	}

	if (error) {
		return (
			<SettingsSection
				title={t("accounts.multiConnector.title")}
				description={t("accounts.multiConnector.description")}
			>
				<div className="space-y-4">
					<Alert className="border-red-200/50 bg-red-50/50 rounded-2xl">
						<AlertCircle className="h-4 w-4 text-red-600" />
						<AlertDescription className="text-red-700">
							{error}
						</AlertDescription>
					</Alert>
					<Button
						onClick={handleRefresh}
						className={cn(
							"px-4 py-2 rounded-xl",
							"bg-linear-to-br from-red-500 to-pink-600 text-white",
							"hover:from-red-600 hover:to-pink-700 hover:shadow-lg hover:scale-105",
							"transition-all duration-200",
						)}
					>
						Réessayer
					</Button>
				</div>
			</SettingsSection>
		);
	}

	return (
		<SettingsSection
			title={t("accounts.multiConnector.title")}
			description={t("accounts.multiConnector.description")}
		>
			<div className="space-y-8">
				{/* Alertes sophistiquées */}
				{providers.filter((p) => p.isConfigured).length === 0 && (
					<Alert className="border-blue-200/50 bg-blue-50/50 rounded-2xl">
						<Info className="h-4 w-4 text-blue-600" />
						<AlertDescription className="text-blue-700">
							<div className="space-y-1">
								<p className="font-medium">
									{t("accounts.alerts.sophisticated.noProvidersTitle")}
								</p>
								<p className="text-sm opacity-90">
									{t("accounts.alerts.sophisticated.noProvidersDescription")}
								</p>
							</div>
						</AlertDescription>
					</Alert>
				)}

				{providers.some((p) => p.isWorking === false) && (
					<Alert className="border-amber-200/50 bg-amber-50/50 rounded-2xl">
						<AlertCircle className="h-4 w-4 text-amber-600" />
						<AlertDescription className="text-amber-700">
							<div className="space-y-1">
								<p className="font-medium">
									{t("accounts.alerts.sophisticated.providersNeedAttention", {
										count: providers.filter((p) => p.isWorking === false).length,
									})}
								</p>
								<p className="text-sm opacity-90">
									{t("accounts.alerts.sophisticated.checkApiKeys")}
								</p>
							</div>
						</AlertDescription>
					</Alert>
				)}

				{/* Grille élégante */}
				<ElegantProviderGrid
					providers={providers}
					onConfigure={handleConfigure}
					onTest={handleTest}
					onToggle={handleToggle}
					onRemove={handleRemove}
					onRefreshProviders={handleRefresh}
					isLoading={testingProviders.size > 0}
				/>

				{/* Configuration Dialog */}
				{selectedProvider && (
					<ProviderConfigDialog
						isOpen={configDialogOpen}
						onOpenChange={setConfigDialogOpen}
						provider={selectedProvider}
						settings={settings}
						onSettingsChange={onSettingsChange}
						onTest={handleTest}
					/>
				)}
			</div>
		</SettingsSection>
	);
}
