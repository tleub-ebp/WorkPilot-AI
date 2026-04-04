import { Globe, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { ProviderModel } from "../../../shared/constants/models";
import { toast } from "../../hooks/use-toast";
import { saveSettings, useSettingsStore } from "../../stores/settings-store";
import { useProviderContext } from "../ProviderContext";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Separator } from "../ui/separator";
import { SettingsSection } from "./SettingsSection";

/**
 * Configuration component for custom/enterprise providers
 * Allows users to configure API endpoints and discover available models
 */
export function CustomProviderConfig() {
	const { t } = useTranslation("settings");
	const settings = useSettingsStore((state) => state.settings);
	const { selectedProvider } = useProviderContext();

	const [isDiscovering, setIsDiscovering] = useState(false);
	const [newModelName, setNewModelName] = useState("");
	const [newModelId, setNewModelId] = useState("");
	const [newModelTier, setNewModelTier] = useState<
		"flagship" | "standard" | "fast"
	>("standard");
	const [newModelSupportsThinking, setNewModelSupportsThinking] =
		useState(false);

	// Only show for custom provider
	if (selectedProvider !== "custom") {
		return null;
	}

	const customModels = settings.customProviderModels || [];

	const handleDiscoverModels = async () => {
		if (!settings.customProviderUrl) {
			toast({
				title: t("customProvider.urlRequired"),
				description: t("customProvider.urlRequiredDesc"),
				variant: "destructive",
			});
			return;
		}

		setIsDiscovering(true);
		try {
			const response = await fetch(`${settings.customProviderUrl}/models`, {
				headers: settings.customProviderApiKey
					? { Authorization: `Bearer ${settings.customProviderApiKey}` }
					: undefined,
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			const data = await response.json();
			const discoveredModels: ProviderModel[] = [];

			// Handle different API formats (OpenAI, HuggingFace, etc.)
			if (Array.isArray(data.data)) {
				// OpenAI-style API
				// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
				data.data.forEach((model: any, index: number) => {
					discoveredModels.push({
						value: model.id || `model-${index}`,
						label: model.id || `Model ${index + 1}`,
						tier: getTierFromModelName(model.id || ""),
						supportsThinking:
							model.id?.toLowerCase().includes("thinking") ||
							model.id?.toLowerCase().includes("reasoning") ||
							model.id?.toLowerCase().includes("deepseek"),
					});
				});
			} else if (Array.isArray(data)) {
				// Direct array of models
				// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
				data.forEach((model: any, index: number) => {
					discoveredModels.push({
						value: model.id || model.name || `model-${index}`,
						label: model.name || model.id || `Model ${index + 1}`,
						tier: getTierFromModelName(model.name || model.id || ""),
						supportsThinking:
							(model.name || model.id || "")
								.toLowerCase()
								.includes("thinking") ||
							(model.name || model.id || "")
								.toLowerCase()
								.includes("reasoning") ||
							(model.name || model.id || "").toLowerCase().includes("deepseek"),
					});
				});
			}

			if (discoveredModels.length > 0) {
				await saveSettings({ customProviderModels: discoveredModels });
				toast({
					title: t("customProvider.modelsDiscovered"),
					description: t("customProvider.modelsDiscoveredDesc", {
						count: discoveredModels.length,
					}),
				});
			} else {
				toast({
					title: t("customProvider.noModelsFound"),
					description: t("customProvider.noModelsFoundDesc"),
					variant: "destructive",
				});
			}
		} catch (error) {
			console.error("Failed to discover models:", error);
			toast({
				title: t("customProvider.discoveryFailed"),
				description:
					error instanceof Error
						? error.message
						: t("customProvider.discoveryFailedDesc"),
				variant: "destructive",
			});
		} finally {
			setIsDiscovering(false);
		}
	};

	const getTierFromModelName = (
		modelName: string,
	): "flagship" | "standard" | "fast" => {
		const name = modelName.toLowerCase();
		if (
			name.includes("gpt-4") ||
			name.includes("claude-3") ||
			name.includes("gemini-pro") ||
			name.includes("llama-3") ||
			name.includes("mixtral") ||
			name.includes("opus")
		) {
			return "flagship";
		} else if (
			name.includes("gpt-3.5") ||
			name.includes("claude-instant") ||
			name.includes("gemini")
		) {
			return "standard";
		}
		return "fast";
	};

	const handleAddCustomModel = async () => {
		if (!newModelName || !newModelId) {
			toast({
				title: t("customProvider.modelInfoRequired"),
				description: t("customProvider.modelInfoRequiredDesc"),
				variant: "destructive",
			});
			return;
		}

		const newModel: ProviderModel = {
			value: newModelId,
			label: newModelName,
			tier: newModelTier,
			supportsThinking: newModelSupportsThinking,
		};

		const updatedModels = [...customModels, newModel];
		await saveSettings({ customProviderModels: updatedModels });

		// Reset form
		setNewModelName("");
		setNewModelId("");
		setNewModelTier("standard");
		setNewModelSupportsThinking(false);

		toast({
			title: t("customProvider.modelAdded"),
			description: t("customProvider.modelAddedDesc", { name: newModelName }),
		});
	};

	const handleRemoveModel = async (modelValue: string) => {
		const updatedModels = customModels.filter((m) => m.value !== modelValue);
		await saveSettings({ customProviderModels: updatedModels });

		toast({
			title: t("customProvider.modelRemoved"),
			description: t("customProvider.modelRemovedDesc"),
		});
	};

	return (
		<SettingsSection
			title={t("customProvider.title")}
			description={t("customProvider.description")}
		>
			<div className="space-y-6">
				{/* API Configuration */}
				<div className="space-y-4">
					<h3 className="text-sm font-medium text-foreground">
						{t("customProvider.apiConfig")}
					</h3>

					<div className="space-y-3">
						<div>
							<Label
								htmlFor="custom-url"
								className="text-xs text-muted-foreground"
							>
								{t("customProvider.apiUrl")}
							</Label>
							<Input
								id="custom-url"
								placeholder="https://api.company.com/v1"
								value={settings.customProviderUrl || ""}
								onChange={(e) =>
									saveSettings({ customProviderUrl: e.target.value })
								}
								className="mt-1"
							/>
						</div>

						<div>
							<Label
								htmlFor="custom-key"
								className="text-xs text-muted-foreground"
							>
								{t("customProvider.apiKey")}
							</Label>
							<Input
								id="custom-key"
								type="password"
								placeholder="sk-..."
								value={settings.customProviderApiKey || ""}
								onChange={(e) =>
									saveSettings({ customProviderApiKey: e.target.value })
								}
								className="mt-1"
							/>
						</div>
					</div>

					{/* Discover Models Button */}
					<Button
						onClick={handleDiscoverModels}
						disabled={isDiscovering || !settings.customProviderUrl}
						variant="outline"
						size="sm"
						className="w-full"
					>
						<RefreshCw
							className={`h-4 w-4 mr-2 ${isDiscovering ? "animate-spin" : ""}`}
						/>
						{isDiscovering
							? t("customProvider.discovering")
							: t("customProvider.discoverModels")}
					</Button>
				</div>

				<Separator />

				{/* Manual Model Management */}
				<div className="space-y-4">
					<h3 className="text-sm font-medium text-foreground">
						{t("customProvider.manualModels")}
					</h3>

					{/* Add Custom Model Form */}
					<div className="space-y-3 p-4 border border-border rounded-lg bg-muted/30">
						<div className="grid grid-cols-2 gap-3">
							<div>
								<Label
									htmlFor="model-name"
									className="text-xs text-muted-foreground"
								>
									{t("customProvider.modelName")}
								</Label>
								<Input
									id="model-name"
									placeholder="Custom Model Name"
									value={newModelName}
									onChange={(e) => setNewModelName(e.target.value)}
									className="mt-1 h-8"
								/>
							</div>
							<div>
								<Label
									htmlFor="model-id"
									className="text-xs text-muted-foreground"
								>
									{t("customProvider.modelId")}
								</Label>
								<Input
									id="model-id"
									placeholder="model-id"
									value={newModelId}
									onChange={(e) => setNewModelId(e.target.value)}
									className="mt-1 h-8"
								/>
							</div>
						</div>

						<div className="flex items-center gap-4">
							<div className="flex items-center space-x-2">
								<Label
									htmlFor="model-tier"
									className="text-xs text-muted-foreground"
								>
									{t("customProvider.modelTier")}
								</Label>
								<select
									id="model-tier"
									value={newModelTier}
									// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
									onChange={(e) => setNewModelTier(e.target.value as any)}
									className="text-xs px-2 py-1 border border-border rounded bg-background"
								>
									<option value="flagship">
										{t("customProvider.tierFlagship")}
									</option>
									<option value="standard">
										{t("customProvider.tierStandard")}
									</option>
									<option value="fast">{t("customProvider.tierFast")}</option>
								</select>
							</div>

							<div className="flex items-center space-x-2">
								<input
									id="model-thinking"
									type="checkbox"
									checked={newModelSupportsThinking}
									onChange={(e) =>
										setNewModelSupportsThinking(e.target.checked)
									}
									className="rounded"
								/>
								<Label
									htmlFor="model-thinking"
									className="text-xs text-muted-foreground"
								>
									{t("customProvider.supportsThinking")}
								</Label>
							</div>

							<Button
								onClick={handleAddCustomModel}
								size="sm"
								className="ml-auto"
							>
								<Plus className="h-3 w-3 mr-1" />
								{t("customProvider.addModel")}
							</Button>
						</div>
					</div>

					{/* Models List */}
					{customModels.length > 0 && (
						<div className="space-y-2">
							<h4 className="text-xs font-medium text-muted-foreground">
								{t("customProvider.availableModels")} ({customModels.length})
							</h4>
							<div className="space-y-1">
								{customModels.map((model) => {
									const tierClasses =
										model.tier === "flagship"
											? "bg-primary/10 text-primary"
											: model.tier === "standard"
												? "bg-blue-500/10 text-blue-600 dark:text-blue-400"
												: "bg-green-500/10 text-green-600 dark:text-green-400";

									return (
										<div
											key={model.value}
											className="flex items-center justify-between p-2 border border-border rounded bg-card"
										>
											<div className="flex items-center gap-2">
												<span className="text-sm font-medium">
													{model.label}
												</span>
												<span className="text-xs text-muted-foreground">
													({model.value})
												</span>
												<span
													className={`inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-medium ${tierClasses}`}
												>
													{t(
														`customProvider.tier${model.tier.charAt(0).toUpperCase() + model.tier.slice(1)}`,
													)}
												</span>
												{model.supportsThinking && (
													<span className="inline-flex items-center rounded bg-violet-500/10 px-1 py-0.5 text-[9px] font-medium text-violet-600 dark:text-violet-400">
														{t("agentProfile.supportsThinking")}
													</span>
												)}
											</div>
											<Button
												onClick={() => handleRemoveModel(model.value)}
												variant="ghost"
												size="sm"
												className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
											>
												<Trash2 className="h-3 w-3" />
											</Button>
										</div>
									);
								})}
							</div>
						</div>
					)}

					{customModels.length === 0 && (
						<div className="text-center py-8 text-muted-foreground">
							<Globe className="h-8 w-8 mx-auto mb-2 opacity-50" />
							<p className="text-sm">
								{t("customProvider.noModelsConfigured")}
							</p>
							<p className="text-xs mt-1">
								{t("customProvider.addModelsDesc")}
							</p>
						</div>
					)}
				</div>
			</div>
		</SettingsSection>
	);
}
