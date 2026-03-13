/**
 * Credential Manager - Service centralisé de gestion des credentials
 *
 * Gère tous les types d'authentification (OAuth, API Key) pour tous les providers
 * Fournit une interface unifiée pour le frontend via IPC
 */

import { EventEmitter } from 'node:events';
import { loadProfilesFile, saveProfilesFile } from '../utils/profile-manager';
import { readSettingsFile } from '../settings-utils';
import type { ProfilesFile } from '../../shared/types/profile';
import { detectProvider } from '../../shared/utils/provider-detection';

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
  private readonly usageData: Map<string, UsageData> = new Map();

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
          console.warn('GitHub CLI check failed:', error instanceof Error ? error.message : error);
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
      if (!this.activeCredential || this.activeCredential?.provider !== provider) {
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
      
      const fs = require('node:fs').promises;
      const path = require('node:path');
      const os = require('node:os');
      
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
        console.log('[CredentialManager] Claude profiles file not found or invalid:', fileError instanceof Error ? fileError.message : fileError);
      }
      
      return { isAuthenticated: false };
    } catch (error) {
      console.warn('[CredentialManager] Failed to check Claude OAuth status:', error);
      return { isAuthenticated: false };
    }
  }

  /**
   * Fetch usage data for Windsurf/Codeium provider.
   * Uses POST to GetTeamCreditBalance with service key.
   * Checks two sources for the service key:
   *   1. API profiles (profiles.json) — Custom Endpoints
   *   2. Global settings (settings.json) — Provider Accounts (globalWindsurfApiKey)
   * Stores the result in the usageData cache and returns it.
   */
  async fetchWindsurfUsage(): Promise<UsageData | null> {
    try {
      let serviceKey: string | undefined;
      let profileId = 'windsurf-global';
      let profileName = 'Windsurf (Codeium)';

      // Source 1: Check API profiles (profiles.json)
      const profilesFile = await loadProfilesFile();
      const windsurfProfile = profilesFile.profiles.find(p => {
        return detectProvider(p.baseUrl) === 'windsurf';
      });

      if (windsurfProfile?.apiKey) {
        serviceKey = windsurfProfile.apiKey;
        profileId = windsurfProfile.id;
        profileName = windsurfProfile.name;
      }

      // Source 2: Fallback to global settings (globalWindsurfApiKey)
      if (!serviceKey) {
        try {
          const settings = readSettingsFile();
          const globalKey = settings?.globalWindsurfApiKey as string | undefined;
          if (globalKey?.trim()) {
            serviceKey = globalKey.trim();
          }
        } catch {
          // Settings file not available
        }
      }

      if (!serviceKey) {
        console.log('[CredentialManager] Windsurf — no service key found in profiles or settings');
        return null;
      }

      const resp = await fetch('https://server.codeium.com/api/v1/GetTeamCreditBalance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service_key: serviceKey }),
        signal: AbortSignal.timeout(10000)
      });

      if (!resp.ok) {
        console.error('[CredentialManager] Windsurf credits API returned error:', resp.status, resp.statusText);
        return null;
      }

      const data = await resp.json();

      // Normalize Codeium response to UsageData format
      const promptCreditsPerSeat = data.promptCreditsPerSeat ?? 0;
      const numSeats = data.numSeats ?? 1;
      const addOnCreditsAvailable = data.addOnCreditsAvailable ?? 0;
      const addOnCreditsUsed = data.addOnCreditsUsed ?? 0;

      const seatCreditsTotal = promptCreditsPerSeat * numSeats;
      const totalCredits = seatCreditsTotal + addOnCreditsAvailable + addOnCreditsUsed;
      const usedCredits = addOnCreditsUsed;

      let sessionPercent = 0;
      if (totalCredits > 0) {
        sessionPercent = Math.round((usedCredits / totalCredits) * 100);
      }

      // Billing cycle progress
      let weeklyPercent = 0;
      const billingStart = data.billingCycleStart ? new Date(data.billingCycleStart).getTime() : 0;
      const billingEnd = data.billingCycleEnd ? new Date(data.billingCycleEnd).getTime() : 0;
      const now = Date.now();
      if (billingEnd > billingStart && now >= billingStart) {
        const cycleDuration = billingEnd - billingStart;
        const elapsed = Math.min(now - billingStart, cycleDuration);
        weeklyPercent = Math.round((elapsed / cycleDuration) * 100);
      }

      const usageResult: UsageData = {
        provider: 'windsurf',
        profileId,
        profileName,
        usage: {
          sessionPercent,
          weeklyPercent,
          sessionResetTimestamp: billingEnd || undefined,
          weeklyResetTimestamp: billingEnd || undefined,
          needsReauthentication: false,
        },
        timestamp: Date.now()
      };

      // Cache it in the usageData Map
      this.usageData.set('windsurf', usageResult);
      this.emit('usage:updated', usageResult);

      return usageResult;
    } catch (error) {
      console.error('[CredentialManager] Windsurf usage fetch failed:', error);
      return null;
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
    if (this.activeCredential?.type !== 'api_key') {
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

/**
 * Detect Windsurf API key from local IDE installation.
 * Uses better-sqlite3 (pure Node.js) to read the state.vscdb SQLite database
 * stored by Windsurf IDE — no Python dependency required.
 *
 * Supports both standard accounts and SSO enterprise accounts by searching
 * multiple keys in the database:
 *   1. windsurfAuthStatus → { apiKey: "sk-ws-..." }
 *   2. codeium.windsurf-windsurf_auth → user name / email
 *   3. windsurf.authToken / codeium.apiKey → SSO enterprise fallback keys
 *
 * Supported paths:
 * - Windows: %APPDATA%/Windsurf/User/globalStorage/state.vscdb
 * - macOS: ~/Library/Application Support/Windsurf/User/globalStorage/state.vscdb
 * - Linux: ~/.config/Windsurf/User/globalStorage/state.vscdb
 */
export async function detectWindsurfLocalToken(): Promise<{ success: boolean; apiKey?: string; userName?: string; error?: string }> {
  try {
    const path = await import('node:path');
    const fs = await import('node:fs');
    const { isWindows, isMacOS } = await import('../platform/index');

    // Determine the state.vscdb path based on platform
    let dbPath: string;
    if (isWindows()) {
      dbPath = path.join(process.env.APPDATA || '', 'Windsurf', 'User', 'globalStorage', 'state.vscdb');
    } else if (isMacOS()) {
      dbPath = path.join(process.env.HOME || '', 'Library', 'Application Support', 'Windsurf', 'User', 'globalStorage', 'state.vscdb');
    } else {
      // Linux
      dbPath = path.join(process.env.HOME || '', '.config', 'Windsurf', 'User', 'globalStorage', 'state.vscdb');
    }

    if (!fs.existsSync(dbPath)) {
      return { success: false, error: 'Windsurf IDE not found. Install Windsurf and sign in first.' };
    }

    // Use better-sqlite3 — pure Node.js, no Python dependency
    let Database: typeof import('better-sqlite3');
    try {
      Database = require('better-sqlite3');
    } catch (e: any) {
      return { success: false, error: `better-sqlite3 module not available: ${e.message}` };
    }

    let db: import('better-sqlite3').Database;
    try {
      db = new Database(dbPath, { readonly: true, fileMustExist: true });
    } catch (e: any) {
      return { success: false, error: `Could not open Windsurf database: ${e.message}` };
    }

    try {
      // Helper to read a key from the ItemTable
      const readKey = (key: string): string | null => {
        try {
          const row = db.prepare('SELECT value FROM ItemTable WHERE key = ?').get(key) as { value: string | Buffer } | undefined;
          if (!row) return null;
          const val = row.value;
          if (Buffer.isBuffer(val)) return val.toString('utf-8');
          return typeof val === 'string' ? val : null;
        } catch {
          return null;
        }
      };

      let apiKey: string | undefined;
      let userName: string | undefined;

      // Strategy 1: Standard auth — windsurfAuthStatus JSON blob with apiKey field
      const authStatusRaw = readKey('windsurfAuthStatus');
      if (authStatusRaw) {
        try {
          const authData = JSON.parse(authStatusRaw);
          if (authData.apiKey) {
            apiKey = authData.apiKey;
          }
          // SSO enterprise: the token may be stored as accessToken or token instead of apiKey
          if (!apiKey && authData.accessToken) {
            apiKey = authData.accessToken;
          }
          if (!apiKey && authData.token) {
            apiKey = authData.token;
          }
          // Extract user info from authStatus if available
          if (authData.userName) userName = authData.userName;
          if (authData.email) userName = userName ? `${userName} (${authData.email})` : authData.email;
          if (authData.name) userName = userName || authData.name;
        } catch {
          // Not valid JSON — treat as raw token string
          if (authStatusRaw.startsWith('sk-') || authStatusRaw.startsWith('eyJ')) {
            apiKey = authStatusRaw;
          }
        }
      }

      // Strategy 2: SSO enterprise fallback keys
      if (!apiKey) {
        // Try windsurf.authToken (used by some SSO enterprise setups)
        const authToken = readKey('windsurf.authToken');
        if (authToken) {
          try {
            const parsed = JSON.parse(authToken);
            apiKey = parsed.apiKey || parsed.accessToken || parsed.token || parsed.key;
          } catch {
            if (authToken.startsWith('sk-') || authToken.startsWith('eyJ') || authToken.length > 40) {
              apiKey = authToken;
            }
          }
        }
      }

      if (!apiKey) {
        // Try codeium.apiKey (direct key storage)
        const codeiumKey = readKey('codeium.apiKey');
        if (codeiumKey && codeiumKey.length > 10) {
          apiKey = codeiumKey;
        }
      }

      if (!apiKey) {
        // Try service-auth/windsurf key pattern (SSO token exchange result)
        const serviceAuth = readKey('service-auth/windsurf');
        if (serviceAuth) {
          try {
            const parsed = JSON.parse(serviceAuth);
            apiKey = parsed.apiKey || parsed.accessToken || parsed.token;
          } catch {
            if (serviceAuth.length > 40) apiKey = serviceAuth;
          }
        }
      }

      // Resolve user name from a separate key if not already found
      if (!userName) {
        const authUserRaw = readKey('codeium.windsurf-windsurf_auth');
        if (authUserRaw) {
          try {
            const parsed = JSON.parse(authUserRaw);
            userName = parsed.name || parsed.userName || parsed.email || authUserRaw;
          } catch {
            userName = authUserRaw;
          }
        }
      }

      db.close();

      if (apiKey) {
        return { success: true, apiKey, userName: userName || undefined };
      }

      // If we found nothing, list available keys for debugging (SSO troubleshooting)
      let debugInfo = '';
      try {
        const reopenedDb = new Database(dbPath, { readonly: true, fileMustExist: true });
        const rows = reopenedDb.prepare(
          "SELECT key FROM ItemTable WHERE key LIKE '%windsurf%' OR key LIKE '%codeium%' OR key LIKE '%auth%' ORDER BY key"
        ).all() as { key: string }[];
        reopenedDb.close();

        if (rows.length > 0) {
          debugInfo = ` Found ${rows.length} related keys: ${rows.map(r => r.key).join(', ')}`;
        }
      } catch { /* ignore debug errors */ }

      return {
        success: false,
        error: `No API key found in Windsurf auth data. Sign in to Windsurf IDE first.${debugInfo}`
      };

    } catch (queryError: any) {
      try { db.close(); } catch { /* ignore */ }
      return { success: false, error: `Error querying Windsurf database: ${queryError.message}` };
    }

  } catch (error: any) {
    return { success: false, error: error.message || 'Unknown error detecting Windsurf token' };
  }
}
