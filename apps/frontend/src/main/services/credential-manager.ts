/**
 * Credential Manager - Service centralisé de gestion des credentials
 *
 * Gère tous les types d'authentification (OAuth, API Key) pour tous les providers
 * Fournit une interface unifiée pour le frontend via IPC
 */

import { EventEmitter } from 'node:events';
import { loadProfilesFile, saveProfilesFile } from '../utils/profile-manager';
import { readSettingsFile, writeSettingsFile } from '../settings-utils';
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
      await this.cleanupTestProfiles();
      await this.loadProfiles();
      this.setupEventHandlers();
    } catch (error) {
      console.error('[CredentialManager] Failed to initialize:', error);
    }
  }

  /**
   * Remove fake/test profiles from profiles.json that were created by ensureTestProfiles.
   * These profiles have placeholder or test-* API keys that cause real API calls to fail.
   */
  private async cleanupTestProfiles(): Promise<void> {
    try {
      const profilesFile = await loadProfilesFile();
      const before = profilesFile.profiles.length;
      profilesFile.profiles = profilesFile.profiles.filter(p => {
        const key = p.apiKey || '';
        const isFake = key.includes('placeholder') || key.startsWith('test-') || (key.startsWith('sk-ant-test') && key.length < 20) || key.length < 20;
        if (isFake) {
          console.log(`[CredentialManager] Removing fake test profile: "${p.name}" (key: ${key.substring(0, 10)}...)`);
        }
        return !isFake;
      });
      if (profilesFile.profiles.length < before) {
        await saveProfilesFile(profilesFile);
        console.log(`[CredentialManager] Cleaned up ${before - profilesFile.profiles.length} fake test profile(s)`);
      }
    } catch {
      // Non-critical — skip cleanup
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
        return;
      }
    }

    // No active API profile — check settings.json for a previously selected provider
    // or a saved Windsurf API key (globalWindsurfApiKey).
    // This ensures the provider selection survives app restarts for SSO/enterprise users.
    try {
      const settings = readSettingsFile();
      const savedProvider = settings?.selectedProvider as string | undefined;
      const windsurfKey = (settings?.globalWindsurfApiKey as string | undefined)?.trim();

      if (savedProvider && savedProvider !== 'anthropic' && savedProvider !== 'claude') {
        console.log(`[CredentialManager] Restoring saved provider from settings: ${savedProvider}`);
        this.activeCredential = {
          provider: savedProvider,
          type: windsurfKey && savedProvider === 'windsurf' ? 'api_key' : 'oauth',
          credentials: windsurfKey && savedProvider === 'windsurf'
            ? { apiKey: windsurfKey }
            : {},
          isActive: true,
          lastValidated: Date.now()
        };
      } else if (windsurfKey) {
        // No selectedProvider saved, but globalWindsurfApiKey exists — user configured Windsurf
        console.log('[CredentialManager] Restoring windsurf provider from globalWindsurfApiKey');
        this.activeCredential = {
          provider: 'windsurf',
          type: 'api_key',
          credentials: { apiKey: windsurfKey },
          isActive: true,
          lastValidated: Date.now()
        };
      }
    } catch {
      // settings file not available — no restoration needed
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

      // Persist selected provider to settings.json so it survives app restarts.
      // This is critical for SSO/enterprise users (e.g., Windsurf) who don't have
      // an API profile in profiles.json — without this, the provider selection is lost.
      try {
        const settings = readSettingsFile() || {};
        settings.selectedProvider = provider;
        writeSettingsFile(settings);
        console.log(`[CredentialManager] Persisted selectedProvider to settings.json: ${provider}`);
      } catch (e) {
        console.warn('[CredentialManager] Failed to persist selectedProvider to settings.json:', e);
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
        const { exec } = require('node:child_process');
        const { promisify } = require('node:util');
        const execAsync = promisify(exec);
        
        try {
          // Tester si GitHub CLI est installé
          const { stdout: version } = await execAsync('gh --version', { timeout: 5000 });
          
          // gh auth status outputs to stderr on Windows, so capture both
          try {
            const { stdout: authStdout, stderr: authStderr } = await execAsync('gh auth status 2>&1', { timeout: 5000 });
            const authOutput = (authStdout || '') + (authStderr || '');
            const isAuthenticated = authOutput.includes('Logged in to') || authOutput.includes('Token:');
            
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
          } catch (authError: any) {
            // gh auth status exits with code 1 when not authenticated — check stderr
            const output = (authError?.stdout || '') + (authError?.stderr || '');
            if (output.includes('Logged in to') || output.includes('Token:')) {
              return {
                success: true,
                message: 'GitHub Copilot authentication (CLI-based)',
                details: { 
                  method: 'GitHub CLI',
                  version: version.trim(),
                  status: 'Authenticated'
                }
              };
            }
            return {
              success: false,
              message: 'GitHub CLI not authenticated. Run: gh auth login'
            };
          }
        } catch (error) {
          console.warn('GitHub CLI check failed:', error instanceof Error ? error.message : error);
          return {
            success: false,
            message: 'GitHub CLI not available. Install GitHub CLI and run: gh auth login'
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

      // Cas spécial pour Windsurf — uses SSO token or service key stored in settings or detected locally
      if (provider === 'windsurf') {
        return await this.testWindsurfProvider();
      }

      // Pour les autres providers (openai, mistral, google, deepseek, grok, ollama, etc.)
      // Source 1: Chercher un profil API dans profiles.json (Custom Endpoints)
      let apiKey: string | undefined;
      let baseUrl: string | undefined;
      let profileName: string | undefined;
      let source = '';

      try {
        const profilesFile = await loadProfilesFile();
        const apiProfile = profilesFile.profiles.find(p => {
          return detectProvider(p.baseUrl) === provider;
        });
        if (apiProfile?.apiKey && !apiProfile.apiKey.includes('placeholder') && !apiProfile.apiKey.startsWith('test-') && apiProfile.apiKey.length >= 20) {
          apiKey = apiProfile.apiKey;
          baseUrl = apiProfile.baseUrl;
          profileName = apiProfile.name;
          source = 'API profile (' + (profileName || 'unnamed') + ')';
        }
      } catch {
        // profiles.json not available
      }

      // Source 2: Chercher dans settings.json (clés API globales)
      // Try multiple possible settings keys for each provider
      if (!apiKey) {
        try {
          const settings = readSettingsFile();
          const globalKeyOptions: Record<string, string[]> = {
            'openai': ['globalOpenAIApiKey'],
            'google': ['globalGoogleDeepMindApiKey', 'globalGoogleApiKey'],
            'gemini': ['globalGoogleApiKey', 'globalGoogleDeepMindApiKey'],
            'mistral': ['globalMistralApiKey'],
            'deepseek': ['globalDeepSeekApiKey'],
            'grok': ['globalGrokApiKey'],
            'meta': ['globalMetaApiKey'],
            'aws': ['globalAWSApiKey'],
            'cursor': ['globalCursorApiKey'],
          };
          const settingsKeys = globalKeyOptions[provider] || [];
          if (settings) {
            for (const settingsKey of settingsKeys) {
              const globalKey = (settings as any)[settingsKey] as string | undefined;
              if (globalKey?.trim()) {
                apiKey = globalKey.trim();
                profileName = provider;
                source = 'global settings (' + settingsKey + ')';
                break;
              }
            }
          }
        } catch {
          // settings file not available
        }
      }

      // Source 3: Vérifier le activeCredential
      if (!apiKey && this.activeCredential?.provider === provider && this.activeCredential.credentials.apiKey) {
        apiKey = this.activeCredential.credentials.apiKey;
        baseUrl = this.activeCredential.credentials.baseUrl;
        profileName = this.activeCredential.credentials.profileName;
        source = 'active credential';
      }

      if (!apiKey) {
        return {
          success: false,
          message: `Provider ${provider} not configured. Add an API key in Custom Endpoints or provider settings.`
        };
      }

      // Debug: log which source provided the key (mask most of the key for security)
      const maskedKey = apiKey.length > 8 ? apiKey.substring(0, 8) + '...' : '***';
      console.log(`[CredentialManager] testProvider(${provider}): key from ${source}, starts with "${maskedKey}", baseUrl=${baseUrl || 'default'}`);

      // Tester la connexion avec le endpoint approprié pour chaque provider
      try {
        const testResult = await this.testApiKeyConnection(provider, apiKey, baseUrl);
        if (testResult.success) {
          return {
            success: true,
            message: `${provider} connection successful`,
            details: {
              method: 'API Key',
              profileName: profileName || provider,
              ...testResult.details
            }
          };
        } else {
          return testResult;
        }
      } catch (testError) {
        return {
          success: false,
          message: testError instanceof Error ? testError.message : `${provider} connection test failed`
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
   * Tester le provider Windsurf (SSO token ou service key)
   * Checks globalWindsurfApiKey in settings, API profiles, and local IDE detection.
   */
  private async testWindsurfProvider(): Promise<{ success: boolean; message: string; details?: any }> {
    try {
      let serviceKey: string | undefined;
      let source = '';

      // Source 1: Check API profiles (profiles.json)
      try {
        const profilesFile = await loadProfilesFile();
        const windsurfProfile = profilesFile.profiles.find(p => {
          return detectProvider(p.baseUrl) === 'windsurf';
        });
        if (windsurfProfile?.apiKey) {
          serviceKey = windsurfProfile.apiKey;
          source = 'API profile';
        }
      } catch {
        // profiles.json not available
      }

      // Source 2: Fallback to global settings (globalWindsurfApiKey)
      if (!serviceKey) {
        try {
          const settings = readSettingsFile();
          const globalKey = settings?.globalWindsurfApiKey as string | undefined;
          if (globalKey?.trim()) {
            serviceKey = globalKey.trim();
            source = 'global settings';
          }
        } catch {
          // Settings file not available
        }
      }

      // Source 3: Try auto-detecting from local Windsurf IDE
      if (!serviceKey) {
        try {
          const detected = await detectWindsurfLocalToken();
          if (detected.success && detected.apiKey) {
            serviceKey = detected.apiKey;
            source = 'local IDE detection';
          }
        } catch {
          // Detection failed
        }
      }

      if (!serviceKey) {
        return {
          success: false,
          message: 'No Windsurf token found. Configure via SSO or provide an API key.'
        };
      }

      // Determine auth method based on token format
      const isServiceKey = serviceKey.startsWith('sk-ws-') || serviceKey.startsWith('sk-');
      const isJWT = serviceKey.startsWith('eyJ');

      if (isServiceKey) {
        // Test with GetTeamCreditBalance API (service key)
        const resp = await fetch('https://server.codeium.com/api/v1/GetTeamCreditBalance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ service_key: serviceKey }),
          signal: AbortSignal.timeout(10000)
        });

        if (resp.ok) {
          return {
            success: true,
            message: 'Windsurf connection successful (service key)',
            details: { method: 'Service Key', source, authType: 'api_key' }
          };
        }

        return {
          success: false,
          message: `Windsurf API returned HTTP ${resp.status}: ${resp.statusText}`
        };
      }

      // For SSO/JWT tokens, validate via a lightweight Codeium API call
      if (isJWT || serviceKey.length > 40) {
        try {
          const resp = await fetch('https://server.codeium.com/exa.api_server_pb.ApiServerService/GetUser', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${serviceKey}`,
            },
            body: '{}',
            signal: AbortSignal.timeout(10000)
          });

          if (resp.ok) {
            return {
              success: true,
              message: 'Windsurf SSO connection successful',
              details: { method: 'SSO/OAuth', source, authType: 'sso' }
            };
          }

          // Even if GetUser fails, the token might still work for the proxy
          // Accept it if it was detected from the local IDE (trusted source)
          if (source === 'local IDE detection') {
            return {
              success: true,
              message: 'Windsurf SSO token detected from local IDE',
              details: { method: 'SSO (local IDE)', source, authType: 'sso' }
            };
          }

          return {
            success: false,
            message: `Windsurf SSO validation returned HTTP ${resp.status}. Token may be expired — try re-authenticating in Windsurf IDE.`
          };
        } catch (e) {
          // Network error on GetUser — still trust local IDE tokens
          if (source === 'local IDE detection' || source === 'global settings') {
            return {
              success: true,
              message: `Windsurf token found (${source})`,
              details: { method: 'SSO', source, authType: 'sso', note: 'API validation unavailable' }
            };
          }
          throw e;
        }
      }

      // Generic token — trust it if it exists
      return {
        success: true,
        message: `Windsurf token configured (${source})`,
        details: { method: 'token', source }
      };

    } catch (error) {
      console.error('[CredentialManager] Windsurf test failed:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Windsurf test failed'
      };
    }
  }

  /**
   * Tester la connexion API pour un provider donné avec une clé API
   * Utilise les endpoints spécifiques à chaque provider pour valider la connexion.
   */
  private async testApiKeyConnection(
    provider: string,
    apiKey: string,
    baseUrl?: string
  ): Promise<{ success: boolean; message: string; details?: any }> {
    try {
      let response: Response;
      const timeout = AbortSignal.timeout(10000);

      switch (provider) {
        case 'openai':
          response = await fetch(`${baseUrl || 'https://api.openai.com'}/v1/models`, {
            headers: { 'Authorization': `Bearer ${apiKey}` },
            signal: timeout
          });
          break;

        case 'google':
        case 'gemini':
          response = await fetch(
            `https://generativelanguage.googleapis.com/v1/models?key=${apiKey}`,
            { signal: timeout }
          );
          break;

        case 'mistral':
          response = await fetch(`${baseUrl || 'https://api.mistral.ai'}/v1/models`, {
            headers: { 'Authorization': `Bearer ${apiKey}` },
            signal: timeout
          });
          break;

        case 'deepseek':
          response = await fetch(`${baseUrl || 'https://api.deepseek.com'}/v1/models`, {
            headers: { 'Authorization': `Bearer ${apiKey}` },
            signal: timeout
          });
          break;

        case 'grok':
          response = await fetch('https://api.x.ai/v1/models', {
            headers: { 'Authorization': `Bearer ${apiKey}` },
            signal: timeout
          });
          break;

        case 'ollama':
          response = await fetch(`${baseUrl || 'http://localhost:11434'}/api/tags`, {
            signal: timeout
          });
          break;

        default:
          // Pour les providers inconnus, vérifier simplement que la clé existe
          if (apiKey && apiKey.trim() !== '') {
            return {
              success: true,
              message: `${provider} API key configured`,
              details: { method: 'API Key (not validated)' }
            };
          }
          return {
            success: false,
            message: `${provider} has no API key configured`
          };
      }

      if (response.ok) {
        const data = await response.json().catch(() => ({}));
        return {
          success: true,
          message: `${provider} connection successful`,
          details: {
            status: response.status,
            modelCount: data.data?.length || data.models?.length || undefined
          }
        };
      } else {
        return {
          success: false,
          message: `${provider} API returned HTTP ${response.status}: ${response.statusText}`
        };
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : `${provider} connection test failed`
      };
    }
  }

  /**
   * Vérifier le statut OAuth Claude
   * Checks multiple sources:
   *   0. App's Claude Profile Manager (hasValidAuth) — checks ~/.claude-profiles/{name}
   *   1. Claude CLI config (Windows: %APPDATA%\claude, Unix: ~/.config/claude)
   *   2. App's own profiles.json for Anthropic API profiles
   *   3. Global settings for globalAnthropicApiKey
   */
  private async checkClaudeOAuthStatus(): Promise<{ isAuthenticated: boolean; profileName?: string }> {
    try {
      // Source 0: Check app's Claude Profile Manager (primary source)
      // This checks ~/.claude-profiles/{profileId}/.credentials.json and Keychain
      try {
        const { getClaudeProfileManager } = require('../claude-profile-manager');
        const profileManager = getClaudeProfileManager();
        if (profileManager) {
          const activeProfile = profileManager.getActiveProfile();
          if (activeProfile && profileManager.hasValidAuth(activeProfile.id)) {
            return {
              isAuthenticated: true,
              profileName: activeProfile.email || activeProfile.name || 'Claude OAuth'
            };
          }
          // Also check all profiles, not just active
          const allProfiles = profileManager.getProfiles?.() || [];
          for (const profile of allProfiles) {
            if (profileManager.hasValidAuth(profile.id)) {
              return {
                isAuthenticated: true,
                profileName: profile.email || profile.name || 'Claude OAuth'
              };
            }
          }
        }
      } catch {
        // Profile manager not initialized yet
      }

      const fs = require('node:fs').promises;
      const path = require('node:path');
      const os = require('node:os');
      
      // Source 1: Check Claude CLI profiles — try multiple paths (Windows + Unix)
      const candidatePaths = [
        // Windows: %APPDATA%\claude\profiles.json
        process.env.APPDATA ? path.join(process.env.APPDATA, 'claude', 'profiles.json') : null,
        // Unix/macOS: ~/.config/claude/profiles.json
        path.join(os.homedir(), '.config', 'claude', 'profiles.json'),
        // Also check Claude Code config
        process.env.APPDATA ? path.join(process.env.APPDATA, 'claude-code', 'profiles.json') : null,
        path.join(os.homedir(), '.config', 'claude-code', 'profiles.json'),
      ].filter(Boolean) as string[];
      
      for (const configPath of candidatePaths) {
        try {
          const profilesData = await fs.readFile(configPath, 'utf-8');
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
        } catch {
          // This path doesn't exist, try next
        }
      }

      // Source 2: Check app's own profiles.json for Anthropic API profile
      try {
        const profilesFile = await loadProfilesFile();
        const anthropicProfile = profilesFile.profiles.find(p => {
          const detected = detectProvider(p.baseUrl);
          return detected === 'anthropic';
        });
        if (anthropicProfile?.apiKey && !anthropicProfile.apiKey.includes('placeholder') && !anthropicProfile.apiKey.startsWith('test-') && anthropicProfile.apiKey.length >= 20) {
          return {
            isAuthenticated: true,
            profileName: anthropicProfile.name || 'Anthropic (API Key)'
          };
        }
      } catch {
        // profiles.json not available
      }

      // Source 3: Check global settings for globalAnthropicApiKey
      try {
        const settings = readSettingsFile();
        const anthropicKey = (settings as any)?.globalAnthropicApiKey as string | undefined;
        if (anthropicKey?.trim()) {
          return {
            isAuthenticated: true,
            profileName: 'Anthropic (API Key)'
          };
        }
      } catch {
        // settings not available
      }
      
      return { isAuthenticated: false };
    } catch (error) {
      console.warn('[CredentialManager] Failed to check Claude OAuth status:', error);
      return { isAuthenticated: false };
    }
  }

  /**
   * Public wrapper for checkClaudeOAuthStatus — used by IPC handlers
   */
  public async checkClaudeOAuthStatusPublic(): Promise<{ isAuthenticated: boolean; profileName?: string }> {
    return this.checkClaudeOAuthStatus();
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

      // Source 3: Auto-detect from local Windsurf IDE (SSO enterprise users)
      if (!serviceKey) {
        try {
          const detected = await detectWindsurfLocalToken();
          if (detected.success && detected.apiKey) {
            serviceKey = detected.apiKey;
            profileName = detected.userName
              ? `Windsurf (${detected.userName})`
              : 'Windsurf (SSO)';
            profileId = 'windsurf-sso';
          }
        } catch {
          // Detection failed
        }
      }

      if (!serviceKey) {
        console.log('[CredentialManager] Windsurf — no service key found in profiles, settings, or local IDE');
        return null;
      }

      const isJWT = serviceKey.startsWith('eyJ');

      // Strategy 1: service_key in body (standard for team service keys — skip for JWT)
      let resp: Response | null = null;
      if (!isJWT) {
        resp = await fetch('https://server.codeium.com/api/v1/GetTeamCreditBalance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ service_key: serviceKey }),
          signal: AbortSignal.timeout(10000)
        });
      }

      // Strategy 2: Bearer header (works for both service keys and SSO/JWT tokens)
      if (!resp || resp.status === 401) {
        resp = await fetch('https://server.codeium.com/api/v1/GetTeamCreditBalance', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${serviceKey}`,
          },
          body: '{}',
          signal: AbortSignal.timeout(10000)
        });
      }

      if (!resp.ok) {
        // Strategy 3: For SSO, try GetTeamInfo
        if (isJWT) {
          try {
            const teamResp = await fetch('https://server.codeium.com/exa.api_server_pb.ApiServerService/GetTeamInfo', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${serviceKey}`,
              },
              body: '{}',
              signal: AbortSignal.timeout(10000)
            });
            if (teamResp.ok) {
              const teamData = await teamResp.json();
              if (teamData && (teamData.promptCreditsPerSeat || teamData.addOnCreditsUsed || teamData.numSeats)) {
                // Normalize teamData the same way as credit balance response
                const tPCS = teamData.promptCreditsPerSeat ?? 0;
                const tNS = teamData.numSeats ?? 1;
                const tACA = teamData.addOnCreditsAvailable ?? 0;
                const tACU = teamData.addOnCreditsUsed ?? 0;
                const tSeatTotal = tPCS * tNS;
                const tTotal = tSeatTotal + tACA + tACU;
                const tUsed = tACU;
                let tPct = 0;
                if (tTotal > 0) tPct = Math.round((tUsed / tTotal) * 100);
                const usageResult: UsageData = {
                  provider: 'windsurf', profileId, profileName,
                  usage: { sessionPercent: tPct, weeklyPercent: 0, needsReauthentication: false },
                  timestamp: Date.now()
                };
                this.usageData.set('windsurf', usageResult);
                this.emit('usage:updated', usageResult);
                return usageResult;
              }
            }
          } catch {
            // GetTeamInfo failed
          }
        }
        console.error('[CredentialManager] Windsurf credits API returned error:', resp.status, resp.statusText);
        // Return a connected-but-no-usage snapshot to prevent Anthropic fallback
        const fallbackResult: UsageData = {
          provider: 'windsurf',
          profileId,
          profileName,
          usage: { sessionPercent: 0, weeklyPercent: 0, needsReauthentication: false },
          timestamp: Date.now()
        };
        this.usageData.set('windsurf', fallbackResult);
        return fallbackResult;
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
        const provider = this.activeCredential.provider;
        const apiKey = this.activeCredential.credentials.apiKey!;
        const baseUrl = this.activeCredential.credentials.baseUrl || '';
        let response: Response;

        switch (provider) {
          case 'anthropic':
          case 'claude':
            response = await fetch(`${baseUrl || 'https://api.anthropic.com'}/v1/models`, {
              headers: {
                'x-api-key': apiKey,
                'anthropic-version': '2023-06-01'
              }
            });
            break;

          case 'openai':
            response = await fetch(`${baseUrl || 'https://api.openai.com'}/v1/models`, {
              headers: { 'Authorization': `Bearer ${apiKey}` }
            });
            break;

          case 'google':
            response = await fetch(
              `https://generativelanguage.googleapis.com/v1/models?key=${apiKey}`
            );
            break;

          case 'mistral':
            response = await fetch(`${baseUrl || 'https://api.mistral.ai'}/v1/models`, {
              headers: { 'Authorization': `Bearer ${apiKey}` }
            });
            break;

          case 'deepseek':
            response = await fetch(`${baseUrl || 'https://api.deepseek.com'}/v1/models`, {
              headers: { 'Authorization': `Bearer ${apiKey}` }
            });
            break;

          case 'grok':
            response = await fetch('https://api.x.ai/v1/models', {
              headers: { 'Authorization': `Bearer ${apiKey}` }
            });
            break;

          case 'ollama':
            response = await fetch(`${baseUrl || 'http://localhost:11434'}/api/tags`);
            break;

          default:
            // Pour les providers inconnus, on considère valide si la clé existe
            if (apiKey && apiKey.trim() !== '') {
              this.activeCredential.lastValidated = Date.now();
              return true;
            }
            return false;
        }

        const isValid = response.ok;
        if (isValid) {
          this.activeCredential.lastValidated = Date.now();
        }
        
        return isValid;
      } else if (this.activeCredential.type === 'oauth') {
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
    const env: Record<string, string> = {};

    // For Windsurf SSO enterprise users: even without an api_key credential,
    // we must inject SELECTED_LLM_PROVIDER so the backend uses WindsurfAgentClient
    // instead of silently falling back to Claude SDK.
    // The backend's windsurf_proxy/auth.py will auto-detect the SSO token from
    // the local Windsurf IDE's state.vscdb database.
    if (this.activeCredential?.provider === 'windsurf') {
      env.SELECTED_LLM_PROVIDER = 'windsurf';

      if (this.activeCredential.type === 'api_key') {
        const apiKey = this.activeCredential.credentials.apiKey || '';
        const baseUrl = this.activeCredential.credentials.baseUrl || '';
        if (apiKey) env.WINDSURF_API_KEY = apiKey;
        if (baseUrl) env.WINDSURF_BASE_URL = baseUrl;
      }
      // For SSO/OAuth type: no WINDSURF_API_KEY needed — backend discovers it
      // from the running Windsurf IDE via state.vscdb

      // Filtrer les valeurs vides
      return Object.fromEntries(
        Object.entries(env).filter(([_, value]) => value.trim() !== '')
      );
    }

    // Fallback: if activeCredential is not set but Windsurf is configured in settings.json
    // (e.g., SSO token saved via ProviderConfigDialog "Save and Connect" button),
    // inject SELECTED_LLM_PROVIDER=windsurf so the backend picks up the right provider.
    if (this.activeCredential?.type !== 'api_key') {
      try {
        const settings = readSettingsFile();
        const windsurfKey = settings?.globalWindsurfApiKey as string | undefined;
        if (windsurfKey?.trim()) {
          env.SELECTED_LLM_PROVIDER = 'windsurf';
          env.WINDSURF_API_KEY = windsurfKey.trim();
          return Object.fromEntries(
            Object.entries(env).filter(([_, value]) => value.trim() !== '')
          );
        }
      } catch {
        // settings file not available
      }
      return {};
    }

    const provider = this.activeCredential.provider;
    const apiKey = this.activeCredential.credentials.apiKey || '';
    const baseUrl = this.activeCredential.credentials.baseUrl || '';

    switch (provider) {
      case 'anthropic':
      case 'claude':
        env.ANTHROPIC_API_KEY = apiKey;
        env.ANTHROPIC_AUTH_TOKEN = apiKey;
        if (baseUrl) env.ANTHROPIC_BASE_URL = baseUrl;
        break;

      case 'openai':
        env.OPENAI_API_KEY = apiKey;
        if (baseUrl) env.OPENAI_BASE_URL = baseUrl;
        break;

      case 'google':
        env.GOOGLE_API_KEY = apiKey;
        break;

      case 'mistral':
        env.MISTRAL_API_KEY = apiKey;
        if (baseUrl) env.MISTRAL_BASE_URL = baseUrl;
        break;

      case 'deepseek':
        env.DEEPSEEK_API_KEY = apiKey;
        if (baseUrl) env.DEEPSEEK_BASE_URL = baseUrl;
        break;

      case 'grok':
        env.GROK_API_KEY = apiKey;
        break;

      case 'meta':
        env.META_API_KEY = apiKey;
        if (baseUrl) env.META_BASE_URL = baseUrl;
        break;

      case 'aws':
        env.AWS_ACCESS_KEY_ID = apiKey;
        if (baseUrl) env.AWS_BEDROCK_ENDPOINT = baseUrl;
        break;

      case 'ollama':
        if (baseUrl) env.OLLAMA_BASE_URL = baseUrl;
        break;

      case 'windsurf':
        env.WINDSURF_API_KEY = apiKey;
        if (baseUrl) env.WINDSURF_BASE_URL = baseUrl;
        break;

      case 'cursor':
        env.CURSOR_API_KEY = apiKey;
        if (baseUrl) env.CURSOR_BASE_URL = baseUrl;
        break;

      default:
        env.LLM_API_KEY = apiKey;
        if (baseUrl) env.LLM_BASE_URL = baseUrl;
        break;
    }

    // Toujours exporter le provider sélectionné pour que le backend sache lequel utiliser
    env.SELECTED_LLM_PROVIDER = provider;

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
 * Helper function to read a key from Windsurf's ItemTable database.
 * Returns the value as a string or null if not found/error.
 */
function readWindsurfKey(db: import('better-sqlite3').Database, key: string): string | null {
  try {
    const row = db.prepare('SELECT value FROM ItemTable WHERE key = ?').get(key) as { value: string | Buffer } | undefined;
    if (!row) return null;
    const val = row.value;
    if (Buffer.isBuffer(val)) return val.toString('utf-8');
    return typeof val === 'string' ? val : null;
  } catch {
    return null;
  }
}

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
      let apiKey: string | undefined;
      let userName: string | undefined;

      // Strategy 1: Standard auth — windsurfAuthStatus JSON blob with apiKey field
      const authStatusRaw = readWindsurfKey(db, 'windsurfAuthStatus');
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
        const authToken = readWindsurfKey(db, 'windsurf.authToken');
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
        const codeiumKey = readWindsurfKey(db, 'codeium.apiKey');
        if (codeiumKey && codeiumKey.length > 10) {
          apiKey = codeiumKey;
        }
      }

      if (!apiKey) {
        // Try service-auth/windsurf key pattern (SSO token exchange result)
        const serviceAuth = readWindsurfKey(db, 'service-auth/windsurf');
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
        const authUserRaw = readWindsurfKey(db, 'codeium.windsurf-windsurf_auth');
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

/**
 * Read cached plan info from the local Windsurf IDE database.
 *
 * The Windsurf IDE caches plan/usage data in its SQLite database (state.vscdb)
 * under the key `windsurf.settings.cachedPlanInfo`. This gives us usage data
 * without needing an API call (which requires Enterprise service keys).
 *
 * Returns the cached plan info if available, or null if Windsurf IDE is not
 * installed or the cache is not available.
 */
export interface WindsurfCachedPlanInfo {
  planName: string;
  startTimestamp: number;
  endTimestamp: number;
  /** True if the cached data is from a previous billing cycle (stale) */
  isStale?: boolean;
  usage: {
    duration: number;
    messages: number;
    flowActions: number;
    flexCredits: number;
    usedMessages: number;
    usedFlowActions: number;
    usedFlexCredits: number;
    remainingMessages: number;
    remainingFlowActions: number;
    remainingFlexCredits: number;
  };
  hasBillingWritePermissions: boolean;
  gracePeriodStatus: number;
}

/**
 * Decode a varint from a Buffer at the given position.
 * Returns [value, newPosition].
 */
function decodeVarint(buf: Buffer, pos: number): [number, number] {
  let result = 0;
  let shift = 0;
  while (pos < buf.length) {
    const b = buf[pos];
    result |= (b & 0x7f) << shift;
    pos++;
    if (!(b & 0x80)) break;
    shift += 7;
  }
  return [result, pos];
}

/**
 * Extract the current billing cycle timestamps from the userStatusProtoBinaryBase64
 * field in windsurfAuthStatus. The protobuf structure is:
 *   - root field 13 (plan info sub-message):
 *     - sub-field 2 (billing start): nested varint at field 1
 *     - sub-field 3 (billing end): nested varint at field 1
 *     - sub-field 8: total messages
 *     - sub-field 9: total flow actions
 */
function extractBillingCycleFromProtobuf(protoB64: string): { startSeconds: number; endSeconds: number; totalMessages: number; totalFlowActions: number; usedMessages: number; usedFlowActions: number } | null {
  try {
    const data = Buffer.from(protoB64, 'base64');
    let pos = 0;

    // Find field 13 in root message
    while (pos < data.length) {
      const [tag, newPos] = decodeVarint(data, pos);
      const fieldNum = tag >> 3;
      const wireType = tag & 0x7;
      pos = newPos;

      if (wireType === 0) {
        // varint — skip
        const [, p] = decodeVarint(data, pos);
        pos = p;
      } else if (wireType === 2) {
        // length-delimited
        const [length, p] = decodeVarint(data, pos);
        pos = p;
        if (fieldNum === 13) {
          // Parse the plan sub-message
          const sub = data.subarray(pos, pos + length);
          let sp = 0;
          let startSeconds = 0;
          let endSeconds = 0;
          let totalMessages = 0;
          let totalFlowActions = 0;
          let usedMessages = 0;
          let usedFlowActions = 0;

          while (sp < sub.length) {
            const [stag, sp2] = decodeVarint(sub, sp);
            const sfn = stag >> 3;
            const swt = stag & 0x7;
            sp = sp2;

            if (swt === 0) {
              const [sv, sp3] = decodeVarint(sub, sp);
              sp = sp3;
              if (sfn === 6) usedMessages = sv;
              if (sfn === 7) usedFlowActions = sv;
              if (sfn === 8) totalMessages = sv;
              if (sfn === 9) totalFlowActions = sv;
            } else if (swt === 2) {
              const [sl, sp3] = decodeVarint(sub, sp);
              sp = sp3;
              const sv = sub.subarray(sp, sp + sl);
              sp += sl;

              // Sub-fields 2 and 3 contain nested messages with a varint at field 1
              if ((sfn === 2 || sfn === 3) && sl > 0) {
                try {
                  const [innerTag, ip2] = decodeVarint(sv, 0);
                  const innerFn = innerTag >> 3;
                  const innerWt = innerTag & 0x7;
                  if (innerFn === 1 && innerWt === 0) {
                    const [ts] = decodeVarint(sv, ip2);
                    if (sfn === 2) startSeconds = ts;
                    if (sfn === 3) endSeconds = ts;
                  }
                } catch { /* skip malformed */ }
              }
            } else if (swt === 5) {
              sp += 4;
            } else if (swt === 1) {
              sp += 8;
            } else {
              break;
            }
          }

          if (startSeconds > 0 && endSeconds > 0) {
            return { startSeconds, endSeconds, totalMessages, totalFlowActions, usedMessages, usedFlowActions };
          }
          return null;
        }
        pos += length;
      } else if (wireType === 5) {
        pos += 4;
      } else if (wireType === 1) {
        pos += 8;
      } else {
        break;
      }
    }
    return null;
  } catch {
    return null;
  }
}

export async function readWindsurfCachedPlanInfo(): Promise<{ success: boolean; planInfo?: WindsurfCachedPlanInfo; userName?: string; error?: string }> {
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
      dbPath = path.join(process.env.HOME || '', '.config', 'Windsurf', 'User', 'globalStorage', 'state.vscdb');
    }

    if (!fs.existsSync(dbPath)) {
      return { success: false, error: 'Windsurf IDE not installed' };
    }

    let Database: typeof import('better-sqlite3');
    try {
      Database = require('better-sqlite3');
    } catch (e: any) {
      return { success: false, error: `better-sqlite3 not available: ${e.message}` };
    }

    let db: import('better-sqlite3').Database;
    try {
      db = new Database(dbPath, { readonly: true, fileMustExist: true });
    } catch (e: any) {
      return { success: false, error: `Could not open Windsurf database: ${e.message}` };
    }

    try {
      // Read cached plan info
      const planInfoRaw = readWindsurfKey(db, 'windsurf.settings.cachedPlanInfo');
      if (!planInfoRaw) {
        db.close();
        return { success: false, error: 'No cached plan info in Windsurf IDE' };
      }

      const planInfo = JSON.parse(planInfoRaw) as WindsurfCachedPlanInfo;

      // Check if the cached plan info is stale (from a previous billing cycle)
      // by comparing with the current billing cycle in the protobuf data.
      // The userStatusProtoBinaryBase64 is refreshed on each IDE session and
      // contains the authoritative billing cycle dates.
      const authStatusRaw = readWindsurfKey(db, 'windsurfAuthStatus');
      if (authStatusRaw) {
        try {
          const authData = JSON.parse(authStatusRaw);
          if (authData.userStatusProtoBinaryBase64) {
            const billing = extractBillingCycleFromProtobuf(authData.userStatusProtoBinaryBase64);
            if (billing) {
              const protoStartMs = billing.startSeconds * 1000;
              const protoEndMs = billing.endSeconds * 1000;

              // The cachedPlanInfo is stale if its endTimestamp <= the protobuf's startTimestamp
              // (meaning it's from the previous billing cycle)
              if (planInfo.endTimestamp <= protoStartMs) {
                console.log('[readWindsurfCachedPlanInfo] Cached plan info is from previous billing cycle, updating from protobuf');
                planInfo.startTimestamp = protoStartMs;
                planInfo.endTimestamp = protoEndMs;
                planInfo.isStale = true;

                // Update totals from protobuf if available
                if (billing.totalMessages > 0) {
                  planInfo.usage.messages = billing.totalMessages;
                }
                if (billing.totalFlowActions > 0) {
                  planInfo.usage.flowActions = billing.totalFlowActions;
                }

                // Use current usage counters from protobuf (field 6 = used messages, field 7 = used flow actions)
                // The protobuf userStatus is refreshed on each IDE session and contains
                // the authoritative current-cycle usage data.
                planInfo.usage.usedMessages = billing.usedMessages;
                planInfo.usage.remainingMessages = Math.max(0, planInfo.usage.messages - billing.usedMessages);
                planInfo.usage.usedFlowActions = billing.usedFlowActions;
                planInfo.usage.remainingFlowActions = Math.max(0, planInfo.usage.flowActions - billing.usedFlowActions);
                planInfo.usage.usedFlexCredits = 0;
                planInfo.usage.remainingFlexCredits = planInfo.usage.flexCredits;

                console.log('[readWindsurfCachedPlanInfo] Updated from protobuf:', {
                  totalMessages: planInfo.usage.messages,
                  usedMessages: planInfo.usage.usedMessages,
                  remainingMessages: planInfo.usage.remainingMessages,
                  totalFlowActions: planInfo.usage.flowActions,
                  usedFlowActions: planInfo.usage.usedFlowActions,
                  remainingFlowActions: planInfo.usage.remainingFlowActions,
                });
              }
              // Cache is current billing cycle — trust cachedPlanInfo usage counters.
              // The protobuf userStatusProtoBinaryBase64 is only refreshed when the IDE
              // starts a new session, so it can be OLDER than cachedPlanInfo which the
              // IDE updates more frequently during active use. Do NOT override usage
              // counters from protobuf as this causes stale data to overwrite fresh data.
              if (billing.usedMessages > 0 && billing.usedMessages !== planInfo.usage.usedMessages) {
                  console.log('[readWindsurfCachedPlanInfo] Cross-check: protobuf usedMessages differs from cache (protobuf may be stale)', {
                    cached: planInfo.usage.usedMessages,
                    protobuf: billing.usedMessages,
                  });
                  // Keep the cachedPlanInfo value — it's updated more frequently by the IDE
              }
            }
          }
        } catch {
          // Failed to parse protobuf — use cached data as-is
        }
      }

      // Read user name from auth data
      let userName: string | undefined;
      const authUserRaw = readWindsurfKey(db, 'codeium.windsurf-windsurf_auth');
      if (authUserRaw) {
        try {
          const parsed = JSON.parse(authUserRaw);
          userName = parsed.name || parsed.userName || parsed.email;
        } catch {
          // If it's not JSON, it's likely the user name string directly
          if (authUserRaw.length > 0 && authUserRaw.length < 200) {
            userName = authUserRaw;
          }
        }
      }

      db.close();
      return { success: true, planInfo, userName };

    } catch (e: any) {
      try { db.close(); } catch { /* ignore */ }
      return { success: false, error: `Error reading Windsurf plan info: ${e.message}` };
    }
  } catch (error: any) {
    return { success: false, error: error.message || 'Unknown error reading Windsurf plan info' };
  }
}

// NOTE: fetchWindsurfRealTimeUsage was removed because the Codeium API
// (GetUserStatus) requires gRPC binary protocol, not REST/JSON. The fetch()
// call always fails with HTTP 400. The root cause of stale credit data was
// the protobuf cross-check in readWindsurfCachedPlanInfo overriding fresh
// cachedPlanInfo values with stale protobuf data. That has been fixed above
// by trusting windsurf.settings.cachedPlanInfo as the primary source.
