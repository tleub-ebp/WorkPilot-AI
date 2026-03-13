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
        if (apiProfile?.apiKey && !apiProfile.apiKey.includes('placeholder')) {
          apiKey = apiProfile.apiKey;
          baseUrl = apiProfile.baseUrl;
          profileName = apiProfile.name;
        }
      } catch {
        // profiles.json not available
      }

      // Source 2: Chercher dans settings.json (clés API globales)
      if (!apiKey) {
        try {
          const settings = readSettingsFile();
          const globalKeyMap: Record<string, string> = {
            'openai': 'globalOpenAIApiKey',
            'google': 'globalGoogleDeepMindApiKey',
            'gemini': 'globalGoogleApiKey',
            'mistral': 'globalMistralApiKey',
            'deepseek': 'globalDeepSeekApiKey',
            'grok': 'globalGrokApiKey',
            'meta': 'globalMetaApiKey',
            'aws': 'globalAWSApiKey',
            'cursor': 'globalCursorApiKey',
          };
          const settingsKey = globalKeyMap[provider];
          if (settingsKey && settings) {
            const globalKey = (settings as any)[settingsKey] as string | undefined;
            if (globalKey?.trim()) {
              apiKey = globalKey.trim();
              profileName = provider;
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
      }

      if (!apiKey) {
        return {
          success: false,
          message: `Provider ${provider} not configured. Add an API key in Custom Endpoints or provider settings.`
        };
      }

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
   *   1. Claude CLI config (Windows: %APPDATA%\claude, Unix: ~/.config/claude)
   *   2. App's own profiles.json for Anthropic API profiles
   *   3. Global settings for globalAnthropicApiKey
   */
  private async checkClaudeOAuthStatus(): Promise<{ isAuthenticated: boolean; profileName?: string }> {
    try {
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
        if (anthropicProfile?.apiKey && !anthropicProfile.apiKey.includes('placeholder')) {
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
    if (this.activeCredential?.type !== 'api_key') {
      return {};
    }

    const provider = this.activeCredential.provider;
    const apiKey = this.activeCredential.credentials.apiKey || '';
    const baseUrl = this.activeCredential.credentials.baseUrl || '';
    const env: Record<string, string> = {};

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
