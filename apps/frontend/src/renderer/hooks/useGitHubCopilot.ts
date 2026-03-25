/**
 * useGitHubCopilot Hook
 * 
 * Hook React pour interagir facilement avec le GitHubCopilotService
 */

import { useState, useEffect, useCallback } from 'react';
import { gitHubCopilotService, type CopilotStatus, type CopilotConfig } from '@shared/services/githubCopilotService';

export interface UseGitHubCopilotReturn {
  // États
  status: CopilotStatus;
  config: CopilotConfig;
  isLoading: boolean;
  error: string | null;

  // Actions
  setToken: (token: string) => Promise<void>;
  removeToken: () => Promise<void>;
  authenticate: () => Promise<void>;
  logout: () => Promise<void>;
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  testConnection: () => Promise<{ success: boolean; message: string; details?: any }>;
  refreshStatus: () => Promise<void>;

  // Utilitaires
  clearError: () => void;
}

/**
 * Hook pour utiliser le GitHub Copilot Service
 */
export function useGitHubCopilot(): UseGitHubCopilotReturn {
  const [status, setStatus] = useState<CopilotStatus>({ installed: false, authenticated: false });
  const [config, setConfig] = useState<CopilotConfig>({ enabled: false });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Charger les données initiales
   */
  const loadInitialData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Charger le statut
      const statusData = await gitHubCopilotService.getStatus();
      setStatus(statusData);

      // Charger la configuration
      const configData = await gitHubCopilotService.getConfig();
      setConfig(configData);

      setIsLoading(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setIsLoading(false);
    }
  }, []);

  /**
   * Configurer le token
   */
  const setToken = useCallback(async (token: string): Promise<void> => {
    try {
      setError(null);
      await gitHubCopilotService.setToken(token);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to set token';
      setError(errorMessage);
      throw err;
    }
  }, []);

  /**
   * Supprimer le token
   */
  const removeToken = useCallback(async (): Promise<void> => {
    try {
      setError(null);
      await gitHubCopilotService.removeToken();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to remove token';
      setError(errorMessage);
      throw err;
    }
  }, []);

  /**
   * Authentifier avec GitHub CLI
   */
  const authenticate = useCallback(async (): Promise<void> => {
    try {
      setError(null);
      await gitHubCopilotService.authenticate();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to authenticate';
      setError(errorMessage);
      throw err;
    }
  }, []);

  /**
   * Se déconnecter
   */
  const logout = useCallback(async (): Promise<void> => {
    try {
      setError(null);
      await gitHubCopilotService.logout();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to logout';
      setError(errorMessage);
      throw err;
    }
  }, []);

  /**
   * Tester la connexion
   */
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  const testConnection = useCallback(async (): Promise<{ success: boolean; message: string; details?: any }> => {
    try {
      setError(null);
      return await gitHubCopilotService.testConnection();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to test connection';
      setError(errorMessage);
      return { success: false, message: errorMessage };
    }
  }, []);

  /**
   * Rafraîchir le statut
   */
  const refreshStatus = useCallback(async (): Promise<void> => {
    try {
      setError(null);
      await gitHubCopilotService.refreshStatus();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to refresh status';
      setError(errorMessage);
    }
  }, []);

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
    const handleStatusUpdated = (newStatus: CopilotStatus) => {
      setStatus(newStatus);
      setIsLoading(false);
    };

    const handleConfigUpdated = (newConfig: CopilotConfig) => {
      setConfig(newConfig);
    };

    gitHubCopilotService.on('status-updated', handleStatusUpdated);
    gitHubCopilotService.on('config-updated', handleConfigUpdated);

    return () => {
      gitHubCopilotService.off('status-updated', handleStatusUpdated);
      gitHubCopilotService.off('config-updated', handleConfigUpdated);
    };
  }, [loadInitialData]);

  return {
    // États
    status,
    config,
    isLoading,
    error,

    // Actions
    setToken,
    removeToken,
    authenticate,
    logout,
    testConnection,
    refreshStatus,

    // Utilitaires
    clearError,
  };
}
