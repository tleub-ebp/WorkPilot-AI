/**
 * GitHub Copilot CLI Service - Frontend service for GitHub Copilot CLI integration
 * 
 * Interface frontend pour communiquer avec le GitHubCopilotService du backend
 */

// Import conditionnel pour éviter les erreurs dans le contexte navigateur
let createIpcListener: any;
let IpcListenerCleanup: any;

try {
  const ipcUtils = require('../../preload/api/modules/ipc-utils');
  createIpcListener = ipcUtils.createIpcListener;
  IpcListenerCleanup = ipcUtils.IpcListenerCleanup;
} catch (error) {
  // En contexte navigateur, ces modules ne sont pas disponibles
  console.warn('[GitHubCopilotService] IPC utils not available in browser context');
  createIpcListener = null;
  IpcListenerCleanup = null;
}

export interface CopilotStatus {
  installed: boolean;
  version?: string;
  authenticated: boolean;
  username?: string;
  token?: string;
  error?: string;
}

export interface CopilotConfig {
  enabled: boolean;
  token?: string;
  username?: string;
}

/**
 * Service de gestion GitHub Copilot CLI côté frontend
 */
class GitHubCopilotServiceClass {
  private eventListeners: Map<string, Set<Function>> = new Map();
  private cleanupFunctions: Map<string, any> = new Map();
  private isInitialized = false;

  constructor() {
    // Ne pas initialiser automatiquement pour éviter les erreurs dans le contexte frontend
    // L'initialisation se fera lors du premier appel
  }

  /**
   * Initialiser les écouteurs d'événements IPC (uniquement si nécessaire)
   */
  private initializeEventListeners(): void {
    if (this.isInitialized || !window.electronAPI || !createIpcListener) return;

    try {
      // Écouter les mises à jour de statut
      const statusCleanup = createIpcListener('github-copilot:status-updated', (status: CopilotStatus) => {
        this.emit('status-updated', status);
      });
      this.cleanupFunctions.set('status-updated', statusCleanup);

      // Écouter les mises à jour de configuration
      const configCleanup = createIpcListener('github-copilot:config-updated', (config: CopilotConfig) => {
        this.emit('config-updated', config);
      });
      this.cleanupFunctions.set('config-updated', configCleanup);
      
      this.isInitialized = true;
    } catch (error) {
      console.warn('[GitHubCopilotService] Failed to initialize event listeners:', error);
    }
  }

  /**
   * S'assurer que le service est initialisé avant toute opération
   */
  private ensureInitialized(): void {
    if (!this.isInitialized) {
      this.initializeEventListeners();
    }
  }

  /**
   * Obtenir le statut de GitHub Copilot CLI
   */
  async getStatus(): Promise<CopilotStatus> {
    this.ensureInitialized();
    
    if (!window.electronAPI?.invoke) {
      console.warn('[GitHubCopilotService] Electron API not available');
      return { installed: false, authenticated: false };
    }

    try {
      return await window.electronAPI.invoke('github-copilot:getStatus');
    } catch (error) {
      console.error('[GitHubCopilotService] Failed to get status:', error);
      return { installed: false, authenticated: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  /**
   * Obtenir la configuration de GitHub Copilot
   */
  async getConfig(): Promise<CopilotConfig> {
    this.ensureInitialized();
    
    if (!window.electronAPI?.invoke) {
      console.warn('[GitHubCopilotService] Electron API not available');
      return { enabled: false };
    }

    try {
      return await window.electronAPI.invoke('github-copilot:getConfig');
    } catch (error) {
      console.error('[GitHubCopilotService] Failed to get config:', error);
      return { enabled: false };
    }
  }

  /**
   * Configurer le token GitHub Copilot
   */
  async setToken(token: string): Promise<void> {
    this.ensureInitialized();
    
    if (!window.electronAPI?.invoke) {
      console.warn('[GitHubCopilotService] Electron API not available');
      return;
    }

    try {
      await window.electronAPI.invoke('github-copilot:setToken', token);
    } catch (error) {
      console.error('[GitHubCopilotService] Failed to set token:', error);
      throw error;
    }
  }

  /**
   * Supprimer le token GitHub Copilot
   */
  async removeToken(): Promise<void> {
    this.ensureInitialized();
    
    if (!window.electronAPI?.invoke) {
      console.warn('[GitHubCopilotService] Electron API not available');
      return;
    }

    try {
      await window.electronAPI.invoke('github-copilot:removeToken');
    } catch (error) {
      console.error('[GitHubCopilotService] Failed to remove token:', error);
      throw error;
    }
  }

  /**
   * Authentifier avec GitHub CLI
   */
  async authenticate(): Promise<void> {
    this.ensureInitialized();
    
    if (!window.electronAPI?.invoke) {
      console.warn('[GitHubCopilotService] Electron API not available');
      return;
    }

    try {
      await window.electronAPI.invoke('github-copilot:authenticate');
    } catch (error) {
      console.error('[GitHubCopilotService] Failed to authenticate:', error);
      throw error;
    }
  }

  /**
   * Se déconnecter
   */
  async logout(): Promise<void> {
    this.ensureInitialized();
    
    if (!window.electronAPI?.invoke) {
      console.warn('[GitHubCopilotService] Electron API not available');
      return;
    }

    try {
      await window.electronAPI.invoke('github-copilot:logout');
    } catch (error) {
      console.error('[GitHubCopilotService] Failed to logout:', error);
      throw error;
    }
  }

  /**
   * Tester la connexion GitHub Copilot
   */
  async testConnection(): Promise<{ success: boolean; message: string; details?: any }> {
    this.ensureInitialized();
    
    if (!window.electronAPI?.invoke) {
      console.warn('[GitHubCopilotService] Electron API not available');
      return { success: false, message: 'Electron API not available' };
    }

    try {
      return await window.electronAPI.invoke('github-copilot:testConnection');
    } catch (error) {
      console.error('[GitHubCopilotService] Failed to test connection:', error);
      return { 
        success: false, 
        message: error instanceof Error ? error.message : 'Test failed' 
      };
    }
  }

  /**
   * Rafraîchir le statut
   */
  async refreshStatus(): Promise<void> {
    this.ensureInitialized();
    
    if (!window.electronAPI?.invoke) {
      console.warn('[GitHubCopilotService] Electron API not available');
      return;
    }

    try {
      await window.electronAPI.invoke('github-copilot:refreshStatus');
    } catch (error) {
      console.error('[GitHubCopilotService] Failed to refresh status:', error);
    }
  }

  /**
   * Obtenir les variables d'environnement
   */
  async getEnvironmentVariables(): Promise<Record<string, string>> {
    this.ensureInitialized();
    
    if (!window.electronAPI?.invoke) {
      console.warn('[GitHubCopilotService] Electron API not available');
      return {};
    }

    try {
      return await window.electronAPI.invoke('github-copilot:getEnv');
    } catch (error) {
      console.error('[GitHubCopilotService] Failed to get environment variables:', error);
      return {};
    }
  }

  /**
   * S'abonner à un événement
   */
  on(event: string, callback: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
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
  private emit(event: string, data: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`[GitHubCopilotService] Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Nettoyage des écouteurs
   */
  cleanup(): void {
    // Nettoyer les écouteurs d'événements IPC
    this.cleanupFunctions.forEach((cleanup, event) => {
      cleanup();
    });
    this.cleanupFunctions.clear();
    
    // Nettoyer les écouteurs internes
    this.eventListeners.clear();
  }
}

// Exporter l'instance singleton
export const gitHubCopilotService = new GitHubCopilotServiceClass();
