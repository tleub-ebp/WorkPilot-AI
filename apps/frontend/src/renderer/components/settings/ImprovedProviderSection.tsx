import { AlertCircle, Loader2 } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Alert, AlertDescription } from "../ui/alert";
import { Button } from "../ui/button";
import { getAllConnectors } from "./multiconnector/utils";
import { ProviderGrid } from "./ProviderGrid";
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

interface ImprovedProviderSectionProps {
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	settings: any;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	onSettingsChange: (settings: any) => void;
	isOpen: boolean;
}

const providerCategories: Record<string, string> = {
	openai: "openai",
	gemini: "google",
	google: "google",
	"meta-llama": "meta",
	meta: "meta",
	mistral: "independent",
	deepseek: "independent",
	grok: "independent",
	windsurf: "independent",
	cursor: "independent",
	"azure-openai": "microsoft",
};

const providerDescriptions: Record<string, string> = {
	openai: "Modèles GPT-5 et autres modèles OpenAI",
	gemini: "Modèles Gemini de Google DeepMind",
	google: "Accès aux API Google et Google DeepMind",
	"meta-llama": "Modèles Llama de Meta via Together.ai",
	meta: "Modèles Meta AI officiels",
	mistral: "Modèles Mistral AI (Mistral, Codéal, etc.)",
	deepseek: "Modèles DeepSeek (DeepSeek-Coder, etc.)",
	grok: "Modèles Grok xAI",
	windsurf: "Provider Windsurf AI",
	cursor: "Provider Cursor AI",
	"azure-openai": "Modèles OpenAI via Azure",
};

export function ImprovedProviderSection({
	settings,
	onSettingsChange,
	isOpen,
}: ImprovedProviderSectionProps) {
	const { t } = useTranslation("settings");
	const [connectors, setConnectors] = useState<
		Array<{ id: string; label: string }>
	>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [testingProviders, setTestingProviders] = useState<Set<string>>(
		new Set(),
	);

	// Charger les connecteurs
	useEffect(() => {
		const loadConnectors = async () => {
			setIsLoading(true);
			setError(null);
			try {
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
		const hasApiKey = apiKeyField && settings[apiKeyField];

		return {
			id: connector.id,
			name: connector.label,
			category,
			description: providerDescriptions[connector.id],
			isConfigured: !!hasApiKey,
			isWorking: hasApiKey ? true : undefined, // On suppose que si la clé existe, ça fonctionne
			lastTested: hasApiKey ? new Date().toISOString() : undefined,
			usageCount: Math.floor(Math.random() * 100), // Simulé pour l'exemple
			isPremium: ["openai", "gemini"].includes(connector.id),
		};
	});

	const handleConfigure = (_providerId: string) => {
		// Ouvrir la configuration du provider
		// TODO: Implémenter la modale de configuration
	};

	const handleTest = async (providerId: string) => {
		setTestingProviders((prev) => new Set(prev).add(providerId));

		try {
			// Simuler un test
			await new Promise((resolve) => setTimeout(resolve, 2000));

			// TODO: Implémenter le vrai test d'API
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
			window.confirm(
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
		// Recharger les providers
		window.location.reload();
	};

	if (isLoading) {
		return (
			<SettingsSection
				title={t("accounts.multiConnector.title")}
				description={t("accounts.multiConnector.description")}
			>
				<div className="flex items-center justify-center p-8">
					<Loader2 className="h-6 w-6 animate-spin mr-2" />
					<span className="text-sm text-muted-foreground">
						Chargement des providers...
					</span>
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
				<Alert variant="destructive">
					<AlertCircle className="h-4 w-4" />
					<AlertDescription>{error}</AlertDescription>
				</Alert>
				<Button onClick={handleRefresh} className="mt-4">
					Réessayer
				</Button>
			</SettingsSection>
		);
	}

	return (
		<SettingsSection
			title={t("accounts.multiConnector.title")}
			description={t("accounts.multiConnector.description")}
		>
			<div className="space-y-6">
				{/* Alertes d'information */}
				{providers.filter((p) => p.isConfigured).length === 0 && (
					<Alert>
						<AlertCircle className="h-4 w-4" />
						<AlertDescription>
							Aucun provider n'est configuré. Configurez au moins un provider
							pour commencer à utiliser l'application.
						</AlertDescription>
					</Alert>
				)}

				{providers.filter((p) => p.isWorking === false).length > 0 && (
					<Alert variant="destructive">
						<AlertCircle className="h-4 w-4" />
						<AlertDescription>
							{providers.filter((p) => p.isWorking === false).length}{" "}
							provider(s) ont des erreurs de configuration. Vérifiez vos clés
							API et réessayez.
						</AlertDescription>
					</Alert>
				)}

				{/* Grille des providers */}
				<ProviderGrid
					providers={providers}
					onConfigure={handleConfigure}
					onTest={handleTest}
					onToggle={handleToggle}
					onRemove={handleRemove}
					onRefreshProviders={handleRefresh}
					isLoading={testingProviders.size > 0}
				/>
			</div>
		</SettingsSection>
	);
}
