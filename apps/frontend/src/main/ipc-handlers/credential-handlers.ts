/**
 * IPC Handlers for Credential Manager
 * 
 * Fournit une interface IPC entre le frontend et le CredentialManager
 */

import { ipcMain } from 'electron';
import { credentialManager } from '../services/credential-manager';
import type { CredentialConfig, UsageData } from '../services/credential-manager';

/**
 * Enregistrer tous les handlers IPC pour les credentials
 */
export function registerCredentialHandlers(): void {
  
  /**
   * Obtenir le credential actif
   */
  ipcMain.handle('credential:getActive', (): CredentialConfig | null => {
    return credentialManager.getActiveCredential();
  });

  /**
   * Définir le provider actif
   */
  ipcMain.handle('credential:setActive', async (event, provider: string, type: 'oauth' | 'api_key', profileId?: string): Promise<void> => {
    await credentialManager.setActiveProvider(provider, type, profileId);
  });

  /**
   * Obtenir les données d'usage pour un provider
   */
  ipcMain.handle('usage:getData', (event, provider: string): UsageData | null => {
    return credentialManager.getUsageData(provider);
  });

  /**
   * Obtenir toutes les données d'usage
   */
  ipcMain.handle('usage:getAllData', (): Record<string, UsageData> => {
    const allData = credentialManager.getAllUsageData();
    // Convertir Map en objet pour la sérialisation JSON
    return Object.fromEntries(allData.entries());
  });

  /**
   * Mettre à jour les données d'usage (appelé par les services d'usage)
   */
  ipcMain.handle('usage:updateData', (event, provider: string, usageData: Partial<UsageData>): void => {
    credentialManager.updateUsageData(provider, usageData);
  });

  /**
   * Valider les credentials actifs
   */
  ipcMain.handle('credential:validate', async (): Promise<boolean> => {
    return await credentialManager.validateActiveCredentials();
  });

  /**
   * Tester un provider (incluant les cas spéciaux)
   */
  ipcMain.handle('credential:testProvider', async (event, provider: string): Promise<{ success: boolean; message: string; details?: any }> => {
    return await credentialManager.testProvider(provider);
  });

  /**
   * Obtenir les variables d'environnement pour le processus Python
   */
  ipcMain.handle('credential:getEnv', (): Record<string, string> => {
    return credentialManager.getEnvironmentVariables();
  });

  /**
   * S'abonner aux événements de credentials
   */
  ipcMain.on('credential:subscribe', (event) => {
    const channel = 'credential:updated';
    
    const onUpdate = (credential: CredentialConfig | null) => {
      event.sender.send(channel, credential);
    };

    credentialManager.on('credential:updated', onUpdate);
    
    // Nettoyage quand la fenêtre est fermée
    event.sender.on('destroyed', () => {
      credentialManager.off('credential:updated', onUpdate);
    });
  });

  /**
   * S'abonner aux événements d'usage
   */
  ipcMain.on('usage:subscribe', (event) => {
    const channel = 'usage:changed';
    
    const onUpdate = (data: UsageData) => {
      event.sender.send(channel, data);
    };

    credentialManager.on('usage:changed', onUpdate);
    
    // Nettoyage quand la fenêtre est fermée
    event.sender.on('destroyed', () => {
      credentialManager.off('usage:changed', onUpdate);
    });
  });

  /**
   * S'abonner aux événements de switch de provider
   */
  ipcMain.on('provider:subscribe', (event) => {
    const channel = 'provider:switched';
    
    const onSwitch = (data: { provider: string; type: 'oauth' | 'api_key' }) => {
      event.sender.send(channel, data);
    };

    credentialManager.on('provider:switched', onSwitch);
    
    // Nettoyage quand la fenêtre est fermée
    event.sender.on('destroyed', () => {
      credentialManager.off('provider:switched', onSwitch);
    });
  });

  console.log('[CredentialHandlers] IPC handlers registered');
}
