/**
 * Credential Service - Frontend service for credential management
 *
 * Interface frontend pour communiquer avec le CredentialManager du backend
 */

export interface CredentialConfig {
	provider: string;
	type: "oauth" | "api_key";
	credentials: {
		accessToken?: string;
		refreshToken?: string;
		expiresAt?: number;
		apiKey?: string;
		baseUrl?: string;
		profileId?: string;
		profileName?: string;
	};
	isActive: boolean;
	lastValidated?: number;
}

export interface UsageData {
	provider: string;
	profileId?: string;
	profileName?: string;
	usage: {
		sessionPercent?: number;
		weeklyPercent?: number;
		sessionUsageValue?: number;
		weeklyUsageValue?: number;
		sessionResetTimestamp?: number;
		weeklyResetTimestamp?: number;
		needsReauthentication?: boolean;
	};
	timestamp: number;
}

/**
 * Service de gestion des credentials côté frontend
 */
class CredentialService {
	private readonly eventListeners: Map<string, Set<Function>> = new Map();

	constructor() {
		this.initializeEventListeners();
	}

	/**
	 * Initialiser les écouteurs d'événements IPC
	 */
	private initializeEventListeners(): void {
		if (!globalThis.electronAPI) {
			console.warn(
				"[CredentialService] Electron API not available - running in browser environment",
			);
			return;
		}

		// Vérifier si les méthodes existent
		if (!globalThis.electronAPI.on) {
			console.warn(
				"[CredentialService] globalThis.electronAPI.on not available - running in development mode",
			);
			return;
		}

		// Écouter les mises à jour de credentials
		globalThis.electronAPI.on(
			"credential:updated",
			(credential: CredentialConfig | null) => {
				this.emit("credential:updated", credential);
			},
		);

		// Écouter les mises à jour d'usage
		globalThis.electronAPI.on("usage:changed", (data: UsageData) => {
			this.emit("usage:changed", data);
		});

		// Écouter les changements de provider
		globalThis.electronAPI.on(
			"provider:switched",
			(data: { provider: string; type: "oauth" | "api_key" }) => {
				this.emit("provider:switched", data);
			},
		);
	}

	/**
	 * Obtenir le credential actif
	 */
	async getActiveCredential(): Promise<CredentialConfig | null> {
		if (!globalThis.electronAPI?.invoke) {
			console.warn("[CredentialService] Electron API not available");
			return null;
		}

		try {
			return await globalThis.electronAPI.invoke("credential:getActive");
		} catch (error) {
			console.error(
				"[CredentialService] Failed to get active credential:",
				error,
			);
			return null;
		}
	}

	/**
	 * Définir le provider actif
	 */
	async setActiveProvider(
		provider: string,
		type: "oauth" | "api_key",
		profileId?: string,
	): Promise<void> {
		if (!globalThis.electronAPI?.invoke) {
			console.warn("[CredentialService] Electron API not available");
			return;
		}

		try {
			await globalThis.electronAPI.invoke(
				"credential:setActive",
				provider,
				type,
				profileId,
			);
		} catch (error) {
			console.error(
				"[CredentialService] Failed to set active provider:",
				error,
			);
			throw error;
		}
	}

	/**
	 * Obtenir les données d'usage pour un provider
	 */
	async getUsageData(provider: string): Promise<UsageData | null> {
		if (!globalThis.electronAPI?.invoke) {
			console.warn("[CredentialService] Electron API not available");
			return null;
		}

		try {
			return await globalThis.electronAPI.invoke("usage:getData", provider);
		} catch (error) {
			console.error("[CredentialService] Failed to get usage data:", error);
			return null;
		}
	}

	/**
	 * Obtenir toutes les données d'usage
	 */
	async getAllUsageData(): Promise<Record<string, UsageData>> {
		if (!globalThis.electronAPI?.invoke) {
			console.warn("[CredentialService] Electron API not available");
			return {};
		}

		try {
			return await globalThis.electronAPI.invoke("usage:getAllData");
		} catch (error) {
			console.error("[CredentialService] Failed to get all usage data:", error);
			return {};
		}
	}

	/**
	 * Mettre à jour les données d'usage
	 */
	async updateUsageData(
		provider: string,
		usageData: Partial<UsageData>,
	): Promise<void> {
		if (!globalThis.electronAPI?.invoke) {
			console.warn("[CredentialService] Electron API not available");
			return;
		}

		try {
			await globalThis.electronAPI.invoke("usage:updateData", provider, usageData);
		} catch (error) {
			console.error("[CredentialService] Failed to update usage data:", error);
		}
	}

	/**
	 * Valider les credentials actifs
	 */
	async validateCredentials(): Promise<boolean> {
		if (!globalThis.electronAPI?.invoke) {
			console.warn("[CredentialService] Electron API not available");
			return false;
		}

		try {
			return await globalThis.electronAPI.invoke("credential:validate");
		} catch (error) {
			console.error(
				"[CredentialService] Failed to validate credentials:",
				error,
			);
			return false;
		}
	}

	/**
	 * Tester un provider (incluant les cas spéciaux comme Copilot)
	 */
	async testProvider(
		provider: string,
	): Promise<{ success: boolean; message: string; details?: unknown }> {
		if (!globalThis.electronAPI?.invoke) {
			console.warn("[CredentialService] Electron API not available");
			return { success: false, message: "Electron API not available" };
		}

		try {
			return await globalThis.electronAPI.invoke(
				"credential:testProvider",
				provider,
			);
		} catch (error) {
			console.error("[CredentialService] Failed to test provider:", error);
			return {
				success: false,
				message: error instanceof Error ? error.message : "Test failed",
			};
		}
	}

	/**
	 * S'abonner à un événement
	 */
	on(event: string, callback: Function): void {
		if (!this.eventListeners.has(event)) {
			this.eventListeners.set(event, new Set());
		}
		this.eventListeners.get(event)?.add(callback);
	}

	/**
	 * Se désabonner d'un événement
	 */
	off(event: string, callback: Function): void {
		const listeners = this.eventListeners.get(event);
		if (listeners) {
			listeners.delete(callback);
			if (listeners.size === 0) {
				this.eventListeners.delete(event);
			}
		}
	}

	/**
	 * Émettre un événement
	 */
	private emit(event: string, data: CredentialConfig | null | UsageData | { provider: string; type: "oauth" | "api_key" }): void {
		const listeners = this.eventListeners.get(event);
		if (listeners) {
			listeners.forEach((callback) => {
				try {
					callback(data);
				} catch (error) {
					console.error(
						`[CredentialService] Error in event listener for ${event}:`,
						error,
					);
				}
			});
		}
	}

	/**
	 * Nettoyage des écouteurs
	 */
	cleanup(): void {
		this.eventListeners.clear();
	}
}

// Exporter l'instance singleton
export const credentialService = new CredentialService();
