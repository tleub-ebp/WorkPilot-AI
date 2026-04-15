/**
 * Credential Integration - Intégration du CredentialManager avec les systèmes existants
 *
 * Ce fichier assure l'intégration entre le nouveau CredentialManager centralisé
 * et les systèmes d'usage existants (usage-monitor, etc.)
 */

import { getUsageMonitor } from "../claude-profile/usage-monitor";
import { credentialManager } from "./credential-manager";

/**
 * Initialiser l'intégration du CredentialManager
 *
 * Cette fonction doit être appelée au démarrage de l'application
 * pour connecter le CredentialManager aux systèmes existants
 */
export async function initializeCredentialIntegration(): Promise<void> {
	try {
		// Obtenir l'instance du monitor d'usage existant
		const usageMonitor = getUsageMonitor();

		// Connecter les événements d'usage du monitor existant au CredentialManager
		if (usageMonitor) {
			// Écouter les mises à jour d'usage existantes
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			usageMonitor.on("usage-updated", (usageData: any) => {
				// Convertir les données d'usage existantes au nouveau format
				const provider = usageData.providerName || "anthropic";

				credentialManager.updateUsageData(provider, {
					provider,
					profileId: usageData.profileId,
					profileName: usageData.profileName,
					usage: {
						sessionPercent: usageData.sessionPercent,
						weeklyPercent: usageData.weeklyPercent,
						sessionUsageValue: usageData.sessionUsageValue,
						weeklyUsageValue: usageData.weeklyUsageValue,
						sessionResetTimestamp: usageData.sessionResetTimestamp,
						weeklyResetTimestamp: usageData.weeklyResetTimestamp,
						needsReauthentication: usageData.needsReauthentication,
					},
					timestamp: Date.now(),
				});
			});

			// Écouter les changements de profils Claude existants
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			usageMonitor.on("profile-changed", (profileData: any) => {
				// Mettre à jour le credential actif quand le profil Claude change
				if (profileData.isAuthenticated) {
					credentialManager.setActiveProvider("anthropic", "oauth");
				} else if (profileData.activeProfileId) {
					credentialManager.setActiveProvider(
						"anthropic",
						"api_key",
						profileData.activeProfileId,
					);
				}
			});
		}

		// Initialiser le CredentialManager avec les données existantes
		await credentialManager.initialize?.();

		// Charger explicitement les données Windsurf du cache local au démarrage
		try {
			const usageMonitor = getUsageMonitor();
			const windsurfUsage = await usageMonitor.getUsageForProvider("windsurf");
			if (windsurfUsage) {
				// Stocker les données normalisées dans le CredentialManager
				credentialManager.updateUsageData("windsurf", {
					provider: "windsurf",
					profileId: windsurfUsage.profileId || "windsurf-local",
					profileName: windsurfUsage.profileName || "Windsurf (Codeium)",
					usage: {
						sessionPercent: windsurfUsage.sessionPercent,
						weeklyPercent: windsurfUsage.weeklyPercent,
						sessionUsageValue: windsurfUsage.sessionUsageValue,
						weeklyUsageValue: windsurfUsage.weeklyUsageValue,
						sessionResetTimestamp: windsurfUsage.sessionResetTimestamp ? new Date(windsurfUsage.sessionResetTimestamp).getTime() : undefined,
						weeklyResetTimestamp: windsurfUsage.weeklyResetTimestamp ? new Date(windsurfUsage.weeklyResetTimestamp).getTime() : undefined,
						needsReauthentication: false,
					},
					timestamp: Date.now(),
				});
			}

			// Poller régulièrement le cache local Windsurf pour avoir des données en temps réel
			// Le cache local est mis à jour par Windsurf IDE à chaque utilisation
			const POLLING_INTERVAL_MS = 30000; // 30 secondes
			setInterval(async () => {
				try {
					const updatedWindsurfUsage = await usageMonitor.getUsageForProvider("windsurf");
					if (updatedWindsurfUsage) {
						// Vérifier si les données ont changé avant de mettre à jour
						const currentData = credentialManager.getUsageData("windsurf");
						const hasChanged = !currentData ||
							currentData.usage?.sessionPercent !== updatedWindsurfUsage.sessionPercent ||
							currentData.usage?.weeklyPercent !== updatedWindsurfUsage.weeklyPercent;

						if (hasChanged) {
							credentialManager.updateUsageData("windsurf", {
								provider: "windsurf",
								profileId: updatedWindsurfUsage.profileId || "windsurf-local",
								profileName: updatedWindsurfUsage.profileName || "Windsurf (Codeium)",
								usage: {
									sessionPercent: updatedWindsurfUsage.sessionPercent,
									weeklyPercent: updatedWindsurfUsage.weeklyPercent,
									sessionUsageValue: updatedWindsurfUsage.sessionUsageValue,
									weeklyUsageValue: updatedWindsurfUsage.weeklyUsageValue,
									sessionResetTimestamp: updatedWindsurfUsage.sessionResetTimestamp ? new Date(updatedWindsurfUsage.sessionResetTimestamp).getTime() : undefined,
									weeklyResetTimestamp: updatedWindsurfUsage.weeklyResetTimestamp ? new Date(updatedWindsurfUsage.weeklyResetTimestamp).getTime() : undefined,
									needsReauthentication: false,
								},
								timestamp: Date.now(),
							});
						}
					}
				} catch (error) {
					console.warn("[CredentialIntegration] Failed to poll Windsurf usage:", error);
				}
			}, POLLING_INTERVAL_MS);
		} catch (error) {
			console.warn("[CredentialIntegration] Failed to load Windsurf usage from cache:", error);
		}
	} catch (error) {
		console.error(
			"[CredentialIntegration] Failed to initialize credential integration:",
			error,
		);
		throw error;
	}
}

/**
 * Obtenir les variables d'environnement pour le processus Python
 *
 * Cette fonction remplace l'ancien getAPIProfileEnv() en utilisant le CredentialManager
 */
export async function getEnvironmentVariables(): Promise<
	Record<string, string>
> {
	return credentialManager.getEnvironmentVariables();
}

/**
 * Basculer vers un provider spécifique
 *
 * Fonction utilitaire pour simplifier le switch de provider
 */
export async function switchToProvider(
	provider: string,
	type: "oauth" | "api_key",
	profileId?: string,
): Promise<void> {
	await credentialManager.setActiveProvider(provider, type, profileId);

	// Notifier les systèmes existants du changement
	const usageMonitor = getUsageMonitor();
	if (usageMonitor?.emit) {
		usageMonitor.emit("provider-switched", { provider, type, profileId });
	}
}

/**
 * Obtenir l'état actuel des credentials et usage
 *
 * Fonction utilitaire pour diagnostiquer l'état du système
 */
export async function getCredentialState(): Promise<{
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	activeCredential: any;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	usageData: Map<string, any>;
	environmentVariables: Record<string, string>;
}> {
	const activeCredential = credentialManager.getActiveCredential();
	const usageData = credentialManager.getAllUsageData();
	const environmentVariables = credentialManager.getEnvironmentVariables();

	return {
		activeCredential,
		usageData,
		environmentVariables,
	};
}
