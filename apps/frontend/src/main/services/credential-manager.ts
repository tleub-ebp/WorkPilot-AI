/**
 * Credential Manager - Service centralisé de gestion des credentials
 *
 * Gère tous les types d'authentification (OAuth, API Key) pour tous les providers
 * Fournit une interface unifiée pour le frontend via IPC
 */

import { EventEmitter } from 'events';
import { loadProfilesFile, saveProfilesFile } from '../utils/profile-manager';
import type { ProfilesFile, APIProfile } from '../../shared/types/profile';

export interface CredentialConfig {
  provider: string;
  type: 'oauth' | 'api_key';
  credentials: {
    // OAuth tokens
    accessToken?: string;
    refreshToken?: string;
    expiresAt?: number;
    
    // API Key
    apiKey?: string;
    baseUrl?: string;
    
    // Métadonnées
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
 * Credential Manager - Gestion centralisée des credentials et usage
 */
export class CredentialManager extends EventEmitter {
  private profiles: ProfilesFile | null = null;
  private activeCredential: CredentialConfig | null = null;
  private usageData: Map<string, UsageData> = new Map();

  constructor() {
    super();
    // L'initialisation est maintenant asynchrone et doit être appelée explicitement
  }

  /**
   * Initialisation du service
   */
  public async initialize(): Promise<void> {
    try {
      await this.loadProfiles();
      this.setupEventHandlers();
    } catch (error) {
      console.error('[CredentialManager] Failed to initialize:', error);
    }
  }

  /**
   * Charger les profils depuis profiles.json
   */
  private async loadProfiles(): Promise<void> {
    this.profiles = await loadProfilesFile();
    
    // Déterminer le credential actif basé sur le profil actif
    if (this.profiles?.activeProfileId) {
      const activeProfile = this.profiles.profiles.find(p => p.id === this.profiles?.activeProfileId);
      if (activeProfile) {
        this.activeCredential = {
          provider: this.detectProviderFromUrl(activeProfile.baseUrl),
          type: 'api_key',
          credentials: {
            apiKey: activeProfile.apiKey,
            baseUrl: activeProfile.baseUrl,
            profileId: activeProfile.id,
            profileName: activeProfile.name
          },
          isActive: true,
          lastValidated: Date.now()
        };
      }
    }
  }

  /**
   * Détecter le provider depuis l'URL de base
   */
  private detectProviderFromUrl(baseUrl: string): string {
    if (baseUrl.includes('anthropic.com')) return 'anthropic';
    if (baseUrl.includes('openai.com')) return 'openai';
    if (baseUrl.includes('api.mistral.ai')) return 'mistral';
    if (baseUrl.includes('generativelanguage.googleapis.com')) return 'google';
    if (baseUrl.includes('api.deepseek.com')) return 'deepseek';
    if (baseUrl.includes('codeium.com') || baseUrl.includes('windsurf.com') || baseUrl.includes('windsurf.ai')) return 'windsurf';
    return 'custom';
  }

  /**
   * Configurer les gestionnaires d'événements
   */
  private setupEventHandlers(): void {
    // Écouter les changements de profils
    this.on('profile:changed', async () => {
      await this.loadProfiles();
      this.emit('credential:updated', this.getActiveCredential());
    });

    // Écouter les mises à jour d'usage
    this.on('usage:updated', (data: UsageData) => {
      this.usageData.set(data.provider, data);
      this.emit('usage:changed', data);
    });
  }

  /**
   * Obtenir le credential actif
   */
  getActiveCredential(): CredentialConfig | null {
    return this.activeCredential;
  }

  /**
   * Définir le provider actif (switch OAuth/API Key)
   */
  async setActiveProvider(provider: string, type: 'oauth' | 'api_key', profileId?: string): Promise<void> {
    try {
      if (type === 'api_key' && profileId) {
        // Mode API Key - utiliser le profil spécifié
        if (!this.profiles) await this.loadProfiles();
        
        const profile = this.profiles?.profiles.find(p => p.id === profileId);
        if (!profile) {
          throw new Error(`Profile ${profileId} not found`);
        }

        // Mettre à jour le profil actif dans profiles.json
        if (this.profiles) {
          this.profiles.activeProfileId = profileId;
          await saveProfilesFile(this.profiles);
        }

        // Mettre à jour le credential actif
        this.activeCredential = {
          provider,
          type: 'api_key',
          credentials: {
            apiKey: profile.apiKey,
            baseUrl: profile.baseUrl,
            profileId: profile.id,
            profileName: profile.name
          },
          isActive: true,
          lastValidated: Date.now()
        };

      } else if (type === 'oauth') {
        // Mode OAuth - désactiver le profil actif
        if (!this.profiles) await this.loadProfiles();
        
        if (this.profiles) {
          this.profiles.activeProfileId = null;
          await saveProfilesFile(this.profiles);
        }

        this.activeCredential = {
          provider,
          type: 'oauth',
          credentials: {
            // Les tokens OAuth seront gérés par le système OAuth existant
          },
          isActive: true,
          lastValidated: Date.now()
        };
      }

      this.emit('credential:updated', this.activeCredential);
      this.emit('provider:switched', { provider, type });

    } catch (error) {
      console.error('[CredentialManager] Failed to set active provider:', error);
      throw error;
    }
  }

  /**
   * Mettre à jour les données d'usage pour un provider
   */
  updateUsageData(provider: string, usageData: Partial<UsageData>): void {
    const existingData = this.usageData.get(provider);
    const updatedData: UsageData = {
      provider,
      usage: {},
      timestamp: Date.now(),
      ...existingData,
      ...usageData
    };

    this.usageData.set(provider, updatedData);
    this.emit('usage:updated', updatedData);
  }

  /**
   * Obtenir les données d'usage pour un provider
   */
  getUsageData(provider: string): UsageData | null {
    return this.usageData.get(provider) || null;
  }

  /**
   * Tester un provider (incluant les cas spéciaux comme Copilot)
   */
  async testProvider(provider: string): Promise<{ success: boolean; message: string; details?: any }> {
    try {
      // Cas spécial pour Copilot - utilise GitHub CLI auth
      if (provider === 'copilot') {
        // Vérifier si GitHub CLI est disponible et authentifié
        const { exec } = require('child_process');
        const { promisify } = require('util');
        const execAsync = promisify(exec);
        
        try {
          // Tester si GitHub CLI est installé
          const { stdout: version } = await execAsync('gh --version', { timeout: 5000 });
          
          // Tester si l'utilisateur est authentifié
          const { stdout: authStatus } = await execAsync('gh auth status', { timeout: 5000 });
          
          const isAuthenticated = authStatus.includes('Logged in to github.com');
          
          if (isAuthenticated) {
            return {
              success: true,
              message: 'GitHub Copilot authentication (CLI-based)',
              details: { 
                method: 'GitHub CLI',
                version: version.trim(),
                status: 'Authenticated'
              }
            };
          } else {
            return {
              success: false,
              message: 'GitHub CLI not authenticated. Run: gh auth login'
            };
          }
        } catch (error) {
          return {
            success: false,
            message: 'GitHub CLI not available or not authenticated. Install and run: gh auth login'
          };
        }
      }

      // Cas spécial pour Anthropic - utilise OAuth
      if (provider === 'anthropic' || provider === 'claude') {
        // Vérifier si un profil OAuth est disponible
        const claudeProfilesResult = await this.checkClaudeOAuthStatus();
        
        if (claudeProfilesResult.isAuthenticated) {
          return {
            success: true,
            message: 'Anthropic OAuth authentication active',
            details: { 
              method: 'OAuth',
              profile: claudeProfilesResult.profileName
            }
          };
        } else {
          return {
            success: false,
            message: 'Anthropic not authenticated. Please sign in with Claude Code or OAuth.'
          };
        }
      }

      // Pour les autres providers, utiliser la logique existante
      if (!this.activeCredential || this.activeCredential.provider !== provider) {
        return {
          success: false,
          message: `Provider ${provider} not configured or not active`
        };
      }

      // Tester la connexion avec le credential actif
      const isValid = await this.validateActiveCredentials();
      
      if (isValid) {
        return {
          success: true,
          message: `${provider} connection successful`,
          details: {
            method: this.activeCredential.type,
            profileName: this.activeCredential.credentials.profileName
          }
        };
      } else {
        return {
          success: false,
          message: `${provider} authentication failed`
        };
      }

    } catch (error) {
      console.error(`[CredentialManager] Test failed for ${provider}:`, error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Test failed'
      };
    }
  }

  /**
   * Vérifier le statut OAuth Claude
   */
  private async checkClaudeOAuthStatus(): Promise<{ isAuthenticated: boolean; profileName?: string }> {
    try {
      // Dans le contexte backend, on ne peut pas utiliser window.electronAPI directement
      // On utilise une approche différente - vérifier les profils Claude via le système de fichiers
      
      const fs = require('fs').promises;
      const path = require('path');
      const os = require('os');
      
      // Chemin vers les profils Claude CLI
      const claudeConfigPath = path.join(os.homedir(), '.config', 'claude', 'profiles.json');
      
      try {
        const profilesData = await fs.readFile(claudeConfigPath, 'utf-8');
        const profiles = JSON.parse(profilesData);
        
        if (profiles.profiles && Array.isArray(profiles.profiles)) {
          const oauthProfile = profiles.profiles.find((profile: any) => 
            profile.isAuthenticated === true
          );
          
          if (oauthProfile) {
            return {
              isAuthenticated: true,
              profileName: oauthProfile.name
            };
          }
        }
      } catch (fileError) {
        // Le fichier n'existe pas ou est invalide
        console.log('[CredentialManager] Claude profiles file not found or invalid');
      }
      
      return { isAuthenticated: false };
    } catch (error) {
      console.warn('[CredentialManager] Failed to check Claude OAuth status:', error);
      return { isAuthenticated: false };
    }
  }

  /**
   * Obtenir toutes les données d'usage
   */
  getAllUsageData(): Map<string, UsageData> {
    return new Map(this.usageData);
  }

  /**
   * Valider les credentials actifs
   */
  async validateActiveCredentials(): Promise<boolean> {
    if (!this.activeCredential) return false;

    try {
      if (this.activeCredential.type === 'api_key') {
        // Valider la clé API via une requête test
        const response = await fetch(`${this.activeCredential.credentials.baseUrl}/v1/models`, {
          headers: {
            'x-api-key': this.activeCredential.credentials.apiKey!,
            'anthropic-version': '2023-06-01'
          }
        });

        const isValid = response.ok;
        if (isValid) {
          this.activeCredential.lastValidated = Date.now();
        }
        
        return isValid;
      } else if (this.activeCredential.type === 'oauth') {
        // La validation OAuth dépend du provider
        // Pour l'instant, on considère que si le token existe, il est valide
        return true;
      }
    } catch (error) {
      console.error('[CredentialManager] Credential validation failed:', error);
      return false;
    }

    return false;
  }

  /**
   * Obtenir les variables d'environnement pour le processus Python
   */
  getEnvironmentVariables(): Record<string, string> {
    if (!this.activeCredential || this.activeCredential.type !== 'api_key') {
      return {};
    }

    const env: Record<string, string> = {
      ANTHROPIC_BASE_URL: this.activeCredential.credentials.baseUrl || '',
      ANTHROPIC_AUTH_TOKEN: this.activeCredential.credentials.apiKey || '',
    };

    // Filtrer les valeurs vides
    return Object.fromEntries(
      Object.entries(env).filter(([_, value]) => value.trim() !== '')
    );
  }

  /**
   * Nettoyage des ressources
   */
  cleanup(): void {
    this.removeAllListeners();
    this.usageData.clear();
    this.profiles = null;
    this.activeCredential = null;
  }
}

// Instance singleton
export const credentialManager = new CredentialManager();
