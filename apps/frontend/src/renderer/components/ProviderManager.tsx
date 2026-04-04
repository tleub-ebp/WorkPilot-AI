import type React from "react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const API_BASE = import.meta.env?.VITE_BACKEND_URL ?? "";

// Squelette de gestion des providers LLM
export const ProviderManager: React.FC<{ selected: string }> = ({
	selected,
}) => {
	const { t } = useTranslation(["providers", "common"]);

	const [_providers, setProviders] = useState<string[]>([]);
	const [_status, setStatus] = useState<Record<string, boolean>>({});
	const [configs, setConfigs] = useState<string[]>([]);
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	const [capabilities, setCapabilities] = useState<any>(null);
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	const [configForm, setConfigForm] = useState<any>({});
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	const [schema, setSchema] = useState<any>(null);
	const [testResult, setTestResult] = useState<string>("");
	const [prompt, setPrompt] = useState<string>("");
	const [generation, setGeneration] = useState<string>("");

	// Ajout : hook pour profils Claude Code
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	const [_claudeProfiles, setClaudeProfiles] = useState<any[]>([]);
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	const [activeClaudeProfile, setActiveClaudeProfile] = useState<any>(null);
	const [claudeModels, setClaudeModels] = useState<string[]>([]);
	const [claudeAuthChecked, setClaudeAuthChecked] = useState(false);

	// Ajout d'un état pour l'erreur
	const [claudeModelsError, setClaudeModelsError] = useState<string>("");
	const [_providersError, setProvidersError] = useState<string>("");

	// Loading states
	// biome-ignore lint/correctness/noUnusedVariables: variable kept for clarity
	const [isLoadingProviders, setIsLoadingProviders] = useState(false);
	const [isLoadingConfigs, setIsLoadingConfigs] = useState(false);
	const [isLoadingCapabilities, setIsLoadingCapabilities] = useState(false);
	const [isLoadingSchema, setIsLoadingSchema] = useState(false);
	const [isLoadingModels, setIsLoadingModels] = useState(false);
	const [isSavingConfig, setIsSavingConfig] = useState(false);
	const [isDeletingConfig, setIsDeletingConfig] = useState(false);
	const [isTestingProvider, setIsTestingProvider] = useState(false);
	const [isGenerating, setIsGenerating] = useState(false);

	useEffect(() => {
		setIsLoadingProviders(true);
		setIsLoadingConfigs(true);

		Promise.all([
			fetch(`${API_BASE}/providers`).then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				const contentType = res.headers.get("content-type");
				if (!contentType?.includes("application/json")) {
					throw new Error("Response is not JSON");
				}
				return res.json();
			}),
			fetch(`${API_BASE}/providers/configs`).then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				const contentType = res.headers.get("content-type");
				if (!contentType?.includes("application/json")) {
					throw new Error("Response is not JSON");
				}
				return res.json();
			}),
		])
			.then(([providersData, configsData]) => {
				setProviders(providersData.providers || []);
				setStatus(providersData.status || {});
				setConfigs(configsData.configs || []);
				setProvidersError("");
			})
			.catch((err) => {
				if (err.message === "Response is not JSON") {
					console.info("[ProviderManager] Backend providers API not available");
				} else {
					console.error("Failed to fetch data:", err);
				}
				setProviders([]);
				setStatus({});
				setConfigs([]);
				setProvidersError(
					`Erreur lors de la récupération des providers: ${err.message}`,
				);
			})
			.finally(() => {
				setIsLoadingProviders(false);
				setIsLoadingConfigs(false);
			});
	}, []);

	useEffect(() => {
		if (selected) {
			setIsLoadingCapabilities(true);
			fetch(`${API_BASE}/providers/capabilities/${selected}`)
				.then((res) => {
					if (!res.ok) throw new Error(`HTTP ${res.status}`);
					const contentType = res.headers.get("content-type");
					if (!contentType?.includes("application/json")) {
						throw new Error("Response is not JSON");
					}
					return res.json();
				})
				.then((data) => setCapabilities(data))
				.catch((err) => {
					console.error("Failed to fetch provider capabilities:", err);
					setCapabilities(null);
				})
				.finally(() => {
					setIsLoadingCapabilities(false);
				});
		} else {
			setCapabilities(null);
			setIsLoadingCapabilities(false);
		}
	}, [selected]);

	useEffect(() => {
		if (selected) {
			setIsLoadingSchema(true);
			Promise.all([
				fetch(`${API_BASE}/providers/schema/${selected}`).then((res) => {
					if (!res.ok) throw new Error(`HTTP ${res.status}`);
					const contentType = res.headers.get("content-type");
					if (!contentType?.includes("application/json")) {
						throw new Error("Response is not JSON");
					}
					return res.json();
				}),
				fetch(`${API_BASE}/providers/config/${selected}`).then((res) => {
					if (!res.ok) throw new Error(`HTTP ${res.status}`);
					const contentType = res.headers.get("content-type");
					if (!contentType?.includes("application/json")) {
						throw new Error("Response is not JSON");
					}
					return res.json();
				}),
			])
				.then(([schemaData, configData]) => {
					setSchema(schemaData);
					setConfigForm(configData || {});
				})
				.catch((err) => {
					console.error("Failed to fetch provider schema/config:", err);
					setSchema(null);
					setConfigForm({});
				})
				.finally(() => {
					setIsLoadingSchema(false);
				});
		} else {
			setSchema(null);
			setConfigForm({});
			setIsLoadingSchema(false);
		}
	}, [selected]);

	useEffect(() => {
		if (globalThis.electronAPI?.requestAllProfilesUsage) {
			globalThis.electronAPI
				.requestAllProfilesUsage()
				.then((result: { success: boolean; data?: { allProfiles?: Array<{ isActive?: boolean }> } }) => {
					if (result?.success && result.data) {
						setClaudeProfiles(result.data.allProfiles || []);
						setActiveClaudeProfile(
							result.data.allProfiles?.find((p) => p.isActive) || null,
						);
					}
					setClaudeAuthChecked(true);
				})
				.catch(() => setClaudeAuthChecked(true));
		} else {
			setClaudeAuthChecked(true);
		}
	}, []);

	useEffect(() => {
		if (!selected) {
			setClaudeModels([]);
			setClaudeModelsError("");
			setIsLoadingModels(false);
			return;
		}
		setIsLoadingModels(true);
		fetch(`${API_BASE}/providers/models/${selected}`)
			.then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				const contentType = res.headers.get("content-type");
				if (!contentType?.includes("application/json")) {
					throw new Error("Response is not JSON");
				}
				return res.json();
			})
			.then((data) => {
				setClaudeModels(data.models || []);
				if (data.error) {
					setClaudeModelsError(data.error);
				} else {
					setClaudeModelsError(
						data.models?.length === 0
							? `Aucun modèle disponible pour le provider «${selected}».`
							: "",
					);
				}
			})
			.catch((err) => {
				console.error("Failed to fetch provider models:", err);
				setClaudeModels([]);
				setClaudeModelsError(`Failed to fetch models: ${err.message}`);
			})
			.finally(() => {
				setIsLoadingModels(false);
			});
	}, [selected]);

	const handleConfigChange = (k: string, v: string) => {
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		setConfigForm((f: any) => ({ ...f, [k]: v }));
	};
	const saveConfig = useCallback(() => {
		setIsSavingConfig(true);
		setTestResult("");
		fetch(`${API_BASE}/providers/config/${selected}`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(configForm),
		})
			.then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				const contentType = res.headers.get("content-type");
				if (!contentType?.includes("application/json")) {
					throw new Error("Response is not JSON");
				}
				return res.json();
			})
			.then(() => globalThis.location.reload())
			.catch((err) => {
				console.error("Failed to save provider config:", err);
				setTestResult(`Failed to save config: ${err.message}`);
			})
			.finally(() => {
				setIsSavingConfig(false);
			});
	}, [selected, configForm]);
	const deleteConfig = useCallback(() => {
		setIsDeletingConfig(true);
		setTestResult("");
		fetch(`${API_BASE}/providers/config/${selected}`, { method: "DELETE" })
			.then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				const contentType = res.headers.get("content-type");
				if (!contentType?.includes("application/json")) {
					throw new Error("Response is not JSON");
				}
				return res.json();
			})
			.then(() => globalThis.location.reload())
			.catch((err) => {
				console.error("Failed to delete provider config:", err);
				setTestResult(`Failed to delete config: ${err.message}`);
			})
			.finally(() => {
				setIsDeletingConfig(false);
			});
	}, [selected]);
	const testProvider = useCallback(() => {
		setIsTestingProvider(true);
		setTestResult("");
		fetch(`${API_BASE}/providers/test/${selected}`, { method: "POST" })
			.then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				const contentType = res.headers.get("content-type");
				if (!contentType?.includes("application/json")) {
					throw new Error("Response is not JSON");
				}
				return res.json();
			})
			.then((data) =>
				setTestResult(data.status || data.detail || JSON.stringify(data)),
			)
			.catch((err) => {
				console.error("Failed to test provider:", err);
				setTestResult(`Failed to test: ${err.message}`);
			})
			.finally(() => {
				setIsTestingProvider(false);
			});
	}, [selected]);
	const handlePrompt = (e: React.ChangeEvent<HTMLInputElement>) =>
		setPrompt(e.target.value);
	const generate = useCallback(() => {
		if (!prompt.trim()) {
			setGeneration("Please enter a prompt first.");
			return;
		}
		setIsGenerating(true);
		setGeneration("");
		fetch(`${API_BASE}/providers/generate/${selected}`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ prompt }),
		})
			.then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				const contentType = res.headers.get("content-type");
				if (!contentType?.includes("application/json")) {
					throw new Error("Response is not JSON");
				}
				return res.json();
			})
			.then((data) =>
				setGeneration(data.result || data.detail || JSON.stringify(data)),
			)
			.catch((err) => {
				console.error("Failed to generate text:", err);
				setGeneration(`Failed to generate: ${err.message}`);
			})
			.finally(() => {
				setIsGenerating(false);
			});
	}, [selected, prompt]);

	return (
		<div>
			<h2>{t("providers:title", "Gestion des providers LLM")}</h2>
			{/* Affichage état Claude Code comme UsageIndicator */}
			{claudeAuthChecked && (
				<div style={{ marginBottom: 12 }}>
					<b>{t("providers:claudeCodeState", "État Claude Code")}&nbsp;:</b>
					{activeClaudeProfile?.isAuthenticated ? (
						<span style={{ color: "green", marginLeft: 8 }}>
							{t("providers:authenticated", "Authentifié")} (
							{activeClaudeProfile.profileName ||
								activeClaudeProfile.profileEmail}
							)
						</span>
					) : (
						<span style={{ color: "orange", marginLeft: 8 }}>
							{t("providers:notAuthenticated", "Non authentifié")}
						</span>
					)}
				</div>
			)}
			{selected && (
				<div style={{ marginTop: 16, border: "1px solid #ccc", padding: 12 }}>
					<h4>
						{t(
							"providers:availableModels",
							"Modèles disponibles pour «" + selected + "»",
							{ provider: selected },
						)}
					</h4>
					{(() => {
						if (isLoadingModels) {
							return (
								<span style={{ color: "blue" }}>
									{t("common:loading", "Chargement...")}
								</span>
							);
						}

						if (claudeModelsError) {
							return (
								<span style={{ color: "red" }}>
									{t("providers:modelError", claudeModelsError, {
										error: claudeModelsError,
									})}
								</span>
							);
						}

						if (claudeModels.length > 0) {
							return (
								<ul>
									{claudeModels.map((m) => (
										<li key={m}>{m}</li>
									))}
								</ul>
							);
						}

						return (
							<span style={{ color: "orange" }}>
								{t(
									"providers:noModels",
									"Aucun modèle détecté ou chargement...",
								)}
							</span>
						);
					})()}
				</div>
			)}
			<div>
				<h3>{t("providers:savedConfigs", "Configurations enregistrées :")}</h3>
				{isLoadingConfigs ? (
					<span style={{ color: "blue" }}>
						{t("common:loading", "Chargement...")}
					</span>
				) : (
					<ul>
						{configs.map((c) => (
							<li key={c}>{c}</li>
						))}
					</ul>
				)}
			</div>
			{selected && (
				<>
					{isLoadingCapabilities ? (
						<div
							style={{ marginTop: 16, border: "1px solid #ccc", padding: 12 }}
						>
							<h3>
								{t(
									"providers:providerCapabilities",
									"Capacités du provider «" + selected + "» :",
									{ provider: selected },
								)}
							</h3>
							<span style={{ color: "blue" }}>
								{t("common:loading", "Chargement...")}
							</span>
						</div>
					) : (
						capabilities && (
							<div>
								<h3>
									{t(
										"providers:providerCapabilities",
										"Capacités du provider «" + selected + "» :",
										{ provider: selected },
									)}
								</h3>
								<pre
									style={{
										background: "#f5f5f5",
										padding: 8,
									}}
								>
									{JSON.stringify(capabilities, null, 2)}
								</pre>
							</div>
						)
					)}
					{isLoadingSchema ? (
						<div
							style={{ marginTop: 16, border: "1px solid #ccc", padding: 12 }}
						>
							<h4>
								{t(
									"providers:configureProvider",
									"Configurer «" + selected + "»",
									{ provider: selected },
								)}
							</h4>
							<span style={{ color: "blue" }}>
								{t("common:loading", "Chargement...")}
							</span>
						</div>
					) : (
						schema && (
							<div
								style={{ marginTop: 16, border: "1px solid #ccc", padding: 12 }}
							>
								<h4>
									{t(
										"providers:configureProvider",
										"Configurer «" + selected + "»",
										{ provider: selected },
									)}
								</h4>
								{Object.entries(schema).map(([k, v]) => (
									<div key={k} style={{ marginBottom: 8 }}>
										<label htmlFor={`config-field-${k}`}>
											{t(`providers:configField_${k}`, k, { field: k })} (
											{String(v)})
										</label>
										<input
											id={`config-field-${k}`}
											type="text"
											value={configForm[k] || ""}
											onChange={(e) => handleConfigChange(k, e.target.value)}
											style={{ marginLeft: 8 }}
										/>
									</div>
								))}
								<button
									type="button"
									onClick={saveConfig}
									disabled={isSavingConfig}
								>
									{isSavingConfig
										? t("common:saving", "Enregistrement...")
										: t("common:save", "Enregistrer")}
								</button>
								<button
									type="button"
									onClick={deleteConfig}
									style={{ marginLeft: 8 }}
									disabled={isDeletingConfig}
								>
									{isDeletingConfig
										? t("common:deleting", "Suppression...")
										: t("common:delete", "Supprimer")}
								</button>
								<button
									type="button"
									onClick={testProvider}
									style={{ marginLeft: 8 }}
									disabled={isTestingProvider}
								>
									{isTestingProvider
										? t("common:testing", "Test...")
										: t("common:test", "Tester")}
								</button>
								{testResult && (
									<span
										style={{
											marginLeft: 8,
											color: testResult.includes("Failed") ? "red" : "green",
										}}
									>
										{testResult}
									</span>
								)}
							</div>
						)
					)}
					<div style={{ marginTop: 16, border: "1px solid #ccc", padding: 12 }}>
						<h4>
							{t(
								"providers:generateWithProvider",
								"Générer avec «" + selected + "»",
								{ provider: selected },
							)}
						</h4>
						<input
							type="text"
							value={prompt}
							onChange={handlePrompt}
							placeholder={t("providers:promptPlaceholder", "Prompt...")}
							style={{ width: 300 }}
							disabled={isGenerating}
						/>
						<button
							type="button"
							onClick={generate}
							style={{ marginLeft: 8 }}
							disabled={isGenerating || !prompt.trim()}
						>
							{isGenerating
								? t("common:generating", "Génération...")
								: t("common:generate", "Générer")}
						</button>
						{generation && (
							<pre style={{ background: "#f5f5f5", padding: 8 }}>
								{generation}
							</pre>
						)}
					</div>
				</>
			)}
		</div>
	);
};
