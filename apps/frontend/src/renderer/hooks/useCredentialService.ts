/**
 * useCredentialService Hook
 *
 * Hook React pour interagir facilement avec le CredentialService
 */

import {
	type CredentialConfig,
	credentialService,
	type UsageData,
} from "@shared/services/credentialService";
import { useCallback, useEffect, useState } from "react";

export interface UseCredentialServiceReturn {
	// États
	activeCredential: CredentialConfig | null;
	usageData: UsageData | null;
	isLoading: boolean;
	isAvailable: boolean;
	error: string | null;

	// Actions
	setActiveProvider: (
		provider: string,
		type: "oauth" | "api_key",
		profileId?: string,
	) => Promise<void>;
	refreshUsageData: (provider?: string) => Promise<void>;
	validateCredentials: () => Promise<boolean>;
	testProvider: (
		provider: string,
	) => Promise<{ success: boolean; message: string; details?: any }>;

	// Utilitaires
	clearError: () => void;
}

/**
 * Hook pour utiliser le CredentialService
 */
export function useCredentialService(
	selectedProvider?: string,
): UseCredentialServiceReturn {
	const [activeCredential, setActiveCredential] =
		useState<CredentialConfig | null>(null);
	const [usageData, setUsageData] = useState<UsageData | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [isAvailable, setIsAvailable] = useState(false);
	const [error, setError] = useState<string | null>(null);

	/**
	 * Charger les données initiales
	 */
	const loadInitialData = useCallback(async () => {
		try {
			setIsLoading(true);
			setError(null);

			// Charger le credential actif
			const credential = await credentialService.getActiveCredential();
			setActiveCredential(credential);

			// Charger les données d'usage si un provider est spécifié
			if (selectedProvider) {
				const usage = await credentialService.getUsageData(selectedProvider);
				setUsageData(usage);
				setIsAvailable(!!usage);
			}

			setIsLoading(false);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : "Unknown error";
			setError(errorMessage);
			setIsLoading(false);
			setIsAvailable(false);
		}
	}, [selectedProvider]);

	/**
	 * Définir le provider actif
	 */
	const setActiveProvider = useCallback(
		async (provider: string, type: "oauth" | "api_key", profileId?: string) => {
			try {
				setError(null);
				await credentialService.setActiveProvider(provider, type, profileId);

				// Recharger les données après le changement
				if (provider === selectedProvider) {
					const usage = await credentialService.getUsageData(provider);
					setUsageData(usage);
					setIsAvailable(!!usage);
				}
			} catch (err) {
				const errorMessage =
					err instanceof Error ? err.message : "Failed to set active provider";
				setError(errorMessage);
				throw err;
			}
		},
		[selectedProvider],
	);

	/**
	 * Rafraîchir les données d'usage
	 */
	const refreshUsageData = useCallback(
		async (provider?: string) => {
			try {
				setError(null);
				const targetProvider = provider || selectedProvider;

				if (targetProvider) {
					const usage = await credentialService.getUsageData(targetProvider);
					setUsageData(usage);
					setIsAvailable(!!usage);
				}
			} catch (err) {
				const errorMessage =
					err instanceof Error ? err.message : "Failed to refresh usage data";
				setError(errorMessage);
			}
		},
		[selectedProvider],
	);

	/**
	 * Valider les credentials
	 */
	const validateCredentials = useCallback(async (): Promise<boolean> => {
		try {
			setError(null);
			const isValid = await credentialService.validateCredentials();
			return isValid;
		} catch (err) {
			const errorMessage =
				err instanceof Error ? err.message : "Failed to validate credentials";
			setError(errorMessage);
			return false;
		}
	}, []);

	/**
	 * Tester un provider
	 */
	const testProvider = useCallback(
		async (
			provider: string,
		): Promise<{ success: boolean; message: string; details?: unknown }> => {
			try {
				setError(null);
				return await credentialService.testProvider(provider);
			} catch (err) {
				const errorMessage =
					err instanceof Error ? err.message : "Failed to test provider";
				setError(errorMessage);
				return { success: false, message: errorMessage };
			}
		},
		[],
	);

	/**
	 * Effacer l'erreur
	 */
	const clearError = useCallback(() => {
		setError(null);
	}, []);

	// Effet pour charger les données initiales et s'abonner aux événements
	useEffect(() => {
		loadInitialData();

		// S'abonner aux événements
		const handleCredentialUpdated = (credential: CredentialConfig | null) => {
			setActiveCredential(credential);
		};

		const handleUsageChanged = (data: UsageData) => {
			if (!selectedProvider || data.provider === selectedProvider) {
				setUsageData(data);
				setIsAvailable(true);
				setIsLoading(false);
			}
		};

		const handleProviderSwitched = (data: {
			provider: string;
			type: "oauth" | "api_key";
		}) => {
			// Recharger les données si le provider switché correspond à celui sélectionné
			if (data.provider === selectedProvider) {
				refreshUsageData(data.provider);
			}
		};

		credentialService.on("credential:updated", handleCredentialUpdated);
		credentialService.on("usage:changed", handleUsageChanged);
		credentialService.on("provider:switched", handleProviderSwitched);

		return () => {
			credentialService.off("credential:updated", handleCredentialUpdated);
			credentialService.off("usage:changed", handleUsageChanged);
			credentialService.off("provider:switched", handleProviderSwitched);
		};
	}, [loadInitialData, selectedProvider, refreshUsageData]);

	return {
		// États
		activeCredential,
		usageData,
		isLoading,
		isAvailable,
		error,

		// Actions
		setActiveProvider,
		refreshUsageData,
		validateCredentials,
		testProvider,

		// Utilitaires
		clearError,
	};
}
