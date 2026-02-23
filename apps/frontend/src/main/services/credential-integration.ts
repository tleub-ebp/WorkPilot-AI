/**
 * Credential Integration - Intégration du CredentialManager avec les systèmes existants
 * 
 * Ce fichier assure l'intégration entre le nouveau CredentialManager centralisé
 * et les systèmes d'usage existants (usage-monitor, etc.)
 */

import { credentialManager } from './credential-manager';
import { getUsageMonitor } from '../claude-profile/usage-monitor';

/**
 * Initialiser l'intégration du CredentialManager
 * 
 * Cette fonction doit être appelée au démarrage de l'application
 * pour connecter le CredentialManager aux systèmes existants
 */
export async function initializeCredentialIntegration(): Promise<void> {
  try {
    console.log('[CredentialIntegration] Initializing credential management integration...');

    // Obtenir l'instance du monitor d'usage existant
    const usageMonitor = getUsageMonitor();

    // Connecter les événements d'usage du monitor existant au CredentialManager
    if (usageMonitor) {
      // Écouter les mises à jour d'usage existantes
      usageMonitor.on('usage-updated', (usageData: any) => {
        // Convertir les données d'usage existantes au nouveau format
        const provider = usageData.providerName || 'anthropic';
        
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
      usageMonitor.on('profile-changed', (profileData: any) => {
        // Mettre à jour le credential actif quand le profil Claude change
        if (profileData.isAuthenticated) {
          credentialManager.setActiveProvider('anthropic', 'oauth');
        } else if (profileData.activeProfileId) {
          credentialManager.setActiveProvider('anthropic', 'api_key', profileData.activeProfileId);
        }
      });

      console.log('[CredentialIntegration] Connected to existing usage monitor');
    }

    // Initialiser le CredentialManager avec les données existantes
    await credentialManager.initialize?.();

    console.log('[CredentialIntegration] Credential management integration initialized successfully');
  } catch (error) {
    console.error('[CredentialIntegration] Failed to initialize credential integration:', error);
    throw error;
  }
}

/**
 * Obtenir les variables d'environnement pour le processus Python
 * 
 * Cette fonction remplace l'ancien getAPIProfileEnv() en utilisant le CredentialManager
 */
export async function getEnvironmentVariables(): Promise<Record<string, string>> {
  return credentialManager.getEnvironmentVariables();
}

/**
 * Basculer vers un provider spécifique
 * 
 * Fonction utilitaire pour simplifier le switch de provider
 */
export async function switchToProvider(
  provider: string, 
  type: 'oauth' | 'api_key', 
  profileId?: string
): Promise<void> {
  await credentialManager.setActiveProvider(provider, type, profileId);
  
  // Notifier les systèmes existants du changement
  const usageMonitor = getUsageMonitor();
  if (usageMonitor && usageMonitor.emit) {
    usageMonitor.emit('provider-switched', { provider, type, profileId });
  }
}

/**
 * Obtenir l'état actuel des credentials et usage
 * 
 * Fonction utilitaire pour diagnostiquer l'état du système
 */
export async function getCredentialState(): Promise<{
  activeCredential: any;
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
