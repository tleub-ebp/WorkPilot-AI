import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { AlertCircle, Key, Globe, Server, CheckCircle, X, Users, LogIn, Loader2, Github } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { AuthTerminal } from './AuthTerminal';
import { GitHubCopilotConfig } from './GitHubCopilotConfig';
import { VisuallyHidden } from '../ui/visually-hidden';
import { cn } from '@/lib/utils';

interface ProviderConfigDialogProps {
  readonly isOpen: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly provider: {
    readonly id: string;
    readonly name: string;
    readonly description?: string;
    readonly isConfigured: boolean;
  } | null;
  readonly settings: any;
  readonly onSettingsChange: (settings: any) => void;
  readonly onTest?: (providerId: string) => Promise<void>;
  readonly useSheet?: boolean; // Nouvelle prop pour savoir si on est dans un Sheet
}

interface ProviderConfig {
  apiKey?: string;
  apiUrl?: string;
  model?: string;
  description: string;
  requiresApiKey: boolean;
  placeholder?: string;
  icon: React.ReactNode;
}

interface AuthTerminalState {
  terminalId: string;
  configDir: string;
  profileName: string;
}

type ActiveTab = 'api' | 'oauth' | 'github-copilot';

export function ProviderConfigDialog({
  isOpen,
  onOpenChange,
  provider,
  settings,
  onSettingsChange,
  onTest,
  useSheet = false
}: ProviderConfigDialogProps) {
  const { t } = useTranslation('settings');
  
  // Mémoriser providerFields pour éviter les recréations infinies
  const providerFields: Record<string, ProviderConfig> = useMemo(() => ({
    'openai': {
      apiKey: 'globalOpenAIApiKey',
      apiUrl: 'globalOpenAIApiBaseUrl',
      model: 'globalOpenAIModel',
      description: t('sections.accounts.providers.openai'),
      requiresApiKey: true,
      placeholder: 'sk-...',
      icon: <Key className="w-4 h-4" />
    },
    'anthropic': {
      apiKey: 'globalAnthropicApiKey',
      description: t('sections.accounts.providers.anthropic'),
      requiresApiKey: true,
      placeholder: 'sk-ant...',
      icon: <Key className="w-4 h-4" />
    },
    'claude': {
      apiKey: 'globalAnthropicApiKey',
      description: t('sections.accounts.providers.anthropic'),
      requiresApiKey: true,
      placeholder: 'sk-ant...',
      icon: <Key className="w-4 h-4" />
    },
    'gemini': {
      apiKey: 'globalGoogleDeepMindApiKey',
      description: t('sections.accounts.providers.google'),
      requiresApiKey: true,
      placeholder: 'AIza...',
      icon: <Key className="w-4 h-4" />
    },
    'google': {
      apiKey: 'globalGoogleDeepMindApiKey',
      description: t('sections.accounts.providers.google'),
      requiresApiKey: true,
      placeholder: 'AIza...',
      icon: <Key className="w-4 h-4" />
    },
    'meta-llama': {
      apiKey: 'globalMetaApiKey',
      description: t('sections.accounts.providers.meta'),
      requiresApiKey: true,
      placeholder: 'META-...',
      icon: <Key className="w-4 h-4" />
    },
    'meta': {
      apiKey: 'globalMetaApiKey',
      description: t('sections.accounts.providers.meta'),
      requiresApiKey: true,
      placeholder: 'META-...',
      icon: <Key className="w-4 h-4" />
    },
    'mistral': {
      apiKey: 'globalMistralApiKey',
      description: t('sections.accounts.providers.mistral'),
      requiresApiKey: true,
      placeholder: 'MISTRAL-...',
      icon: <Key className="w-4 h-4" />
    },
    'deepseek': {
      apiKey: 'globalDeepSeekApiKey',
      description: t('sections.accounts.providers.deepseek'),
      requiresApiKey: true,
      placeholder: 'sk-...',
      icon: <Key className="w-4 h-4" />
    },
    'grok': {
      apiKey: 'globalGrokApiKey',
      description: t('sections.accounts.providers.grok'),
      requiresApiKey: true,
      placeholder: 'xai-...',
      icon: <Key className="w-4 h-4" />
    },
    'windsurf': {
      apiKey: 'globalWindsurfApiKey',
      description: t('sections.accounts.providers.windsurf'),
      requiresApiKey: true,
      placeholder: 'windsurf-...',
      icon: <Key className="w-4 h-4" />
    },
    'cursor': {
      apiKey: 'globalCursorApiKey',
      description: t('sections.accounts.providers.cursor'),
      requiresApiKey: true,
      placeholder: 'crsr-...',
      icon: <Key className="w-4 h-4" />
    },
    'azure-openai': {
      apiKey: 'globalAzureApiKey',
      apiUrl: 'globalAzureApiBaseUrl',
      description: t('sections.accounts.providers.aws'),
      requiresApiKey: true,
      placeholder: 'Azure API Key...',
      icon: <Server className="w-4 h-4" />
    },
    'ollama': {
      apiUrl: 'globalOllamaApiUrl',
      description: t('sections.accounts.providers.ollama'),
      requiresApiKey: false,
      placeholder: 'http://localhost:11434',
      icon: <Server className="w-4 h-4" />
    }
  }), [t]);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>('api');
  const [authTerminal, setAuthTerminal] = useState<AuthTerminalState | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [windsurfSsoToken, setWindsurfSsoToken] = useState('');

  const providerConfig = provider ? providerFields[provider.id] : null;
  const supportsOAuth = ['anthropic', 'claude', 'windsurf'].includes(provider?.id || '');
  const supportsGitHubCopilot = provider?.id === 'copilot';

  const getDefaultActiveTab = (providerId: string, hasOAuthSupport: boolean): ActiveTab => {
    if (providerId === 'copilot') return 'github-copilot';
    if (providerId === 'windsurf') return 'api'; // Windsurf defaults to API key tab, SSO is secondary
    if (hasOAuthSupport) return 'oauth';
    return 'api';
  };

  const initializeFormData = (config: ProviderConfig, currentSettings: any): Record<string, string> => {
    const initialData: Record<string, string> = {};
    
    if (config.apiKey && currentSettings[config.apiKey]) {
      initialData.apiKey = currentSettings[config.apiKey];
    }
    if (config.apiUrl && currentSettings[config.apiUrl]) {
      initialData.apiUrl = currentSettings[config.apiUrl];
    }
    if (config.model && currentSettings[config.model]) {
      initialData.model = currentSettings[config.model];
    }
    
    return initialData;
  };

  useEffect(() => {
    if (!provider || !providerConfig || !isOpen) return;

    const initialData = initializeFormData(providerConfig, settings);
    setFormData(initialData);
    setTestResult(null);
    setActiveTab(getDefaultActiveTab(provider.id, supportsOAuth));
  }, [provider, providerConfig, settings, isOpen, supportsOAuth]);

  const handleSave = async () => {
    if (!provider || !providerConfig) return;

    const newSettings = { ...settings };

    // For Anthropic/Claude on OAuth tab: persist OAuth state instead of API keys
    if ((provider.id === 'anthropic' || provider.id === 'claude') && activeTab === 'oauth') {
      // Always persist OAuth token if auth succeeded (testResult) or if already set in settings
      if (testResult?.success) {
        newSettings.globalClaudeOAuthToken = testResult.message || 'oauth-authenticated';
      } else if (!newSettings.globalClaudeOAuthToken) {
        // Check IPC as fallback — the auth terminal may have written credentials to disk
        // but the settings object doesn't reflect it yet
        try {
          const result = await globalThis.electronAPI?.checkClaudeOAuth?.();
          if (result?.isAuthenticated) {
            newSettings.globalClaudeOAuthToken = result.profileName || 'oauth-authenticated';
          }
        } catch {
          // IPC not available
        }
      }
      onSettingsChange(newSettings);
      onOpenChange(false);
      return;
    }
    
    if (providerConfig.apiKey) {
      newSettings[providerConfig.apiKey] = formData.apiKey || '';
      newSettings[`${providerConfig.apiKey}Enabled`] = !!formData.apiKey;
    }
    if (providerConfig.apiUrl) {
      newSettings[providerConfig.apiUrl] = formData.apiUrl || '';
    }
    if (providerConfig.model) {
      newSettings[providerConfig.model] = formData.model || '';
    }

    onSettingsChange(newSettings);
    onOpenChange(false);
  };

  const handleTest = async () => {
    if (!provider) return;

    setIsTesting(true);
    setTestResult(null);

    try {
      // On OAuth tab for Anthropic/Claude: check OAuth status directly via IPC
      if (activeTab === 'oauth' && (provider.id === 'anthropic' || provider.id === 'claude')) {
        const result = await globalThis.electronAPI?.checkClaudeOAuth?.();
        if (result?.isAuthenticated) {
          setTestResult({ 
            success: true, 
            message: result.profileName 
              ? `Authentification OAuth active (${result.profileName})` 
              : 'Authentification OAuth active' 
          });
        } else {
          setTestResult({ 
            success: false, 
            message: 'Aucune authentification OAuth détectée. Veuillez vous connecter d\'abord.' 
          });
        }
        return;
      }

      // Standard test via parent handler
      if (!onTest) return;
      await onTest(provider.id);
      setTestResult({ success: true, message: t('sections.accounts.providerCard.testSuccess') });
    } catch (error) {
      setTestResult({ 
        success: false, 
        message: error instanceof Error ? error.message : t('sections.accounts.providerCard.testErrorDescription', { error: 'Échec de la connexion. Vérifiez vos paramètres.' })
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleDelete = () => {
    if (!provider || !providerConfig) return;

    if (confirm(t('sections.accounts.providerCard.deleteConfirm', { providerName: provider.name }))) {
      const newSettings = { ...settings };
      
      if (providerConfig.apiKey) {
        newSettings[providerConfig.apiKey] = '';
        newSettings[`${providerConfig.apiKey}Enabled`] = false;
      }
      if (providerConfig.apiUrl) {
        newSettings[providerConfig.apiUrl] = '';
      }
      if (providerConfig.model) {
        newSettings[providerConfig.model] = '';
      }

      // Also clear OAuth token for Anthropic/Claude
      if (provider.id === 'anthropic' || provider.id === 'claude') {
        newSettings.globalClaudeOAuthToken = '';
      }

      onSettingsChange(newSettings);
      onOpenChange(false);
    }
  };

  const handleClaudeAuth = async (providerId: string, providerName: string) => {
    try {
      const profilesResult = await globalThis.electronAPI.getClaudeProfiles();
      const activeProfileId = profilesResult.success && profilesResult.data
        ? profilesResult.data.activeProfileId
        : undefined;

      if (!activeProfileId) {
        console.error('[ProviderConfigDialog] No active Claude profile found');
        setTestResult({ success: false, message: 'No Claude profile found. Please restart the application.' });
        setIsAuthenticating(false);
        return;
      }

      const result = await globalThis.electronAPI.authenticateClaudeProfile(activeProfileId);
      if (result.success && result.data) {
        setAuthTerminal({
          terminalId: result.data.terminalId,
          configDir: result.data.configDir,
          profileName: providerName,
        });
      } else {
        console.error('[ProviderConfigDialog] Failed to prepare Claude auth:', result.error);
        setTestResult({ success: false, message: result.error || 'Failed to prepare authentication' });
        setIsAuthenticating(false);
      }
    } catch (error) {
      console.error('[ProviderConfigDialog] Error preparing Claude auth:', error);
      setTestResult({ success: false, message: error instanceof Error ? error.message : 'Unknown error' });
      setIsAuthenticating(false);
    }
  };

  const handleFallbackAuth = (providerId: string, providerName: string) => {
    const terminalId = `auth-${providerId}-${Date.now()}`;
    const configDir = `claude-config-${providerId}`;
    setAuthTerminal({ terminalId, configDir, profileName: providerName });
  };

  const handleOAuthAuth = async () => {
    if (!provider) return;

    setIsAuthenticating(true);

    if (provider.id === 'anthropic' || provider.id === 'claude') {
      await handleClaudeAuth(provider.id, provider.name);
    } else {
      handleFallbackAuth(provider.id, provider.name);
    }
  };

  const handleAuthTerminalClose = () => {
    setAuthTerminal(null);
    setIsAuthenticating(false);
  };

  const handleAuthTerminalSuccess = (email?: string) => {
    const message = email ? `Authentification réussie pour ${email} !` : 'Authentification réussie !';
    setTestResult({ 
      success: true, 
      message 
    });
    setAuthTerminal(null);
    setIsAuthenticating(false);

    // Persist OAuth state in settings so the provider shows as configured
    if (provider && (provider.id === 'anthropic' || provider.id === 'claude')) {
      const newSettings = { ...settings };
      newSettings.globalClaudeOAuthToken = email || 'oauth-authenticated';
      onSettingsChange(newSettings);
    }
  };

  const handleAuthTerminalError = (error: string) => {
    setTestResult({ 
      success: false, 
      message: `Échec de l'authentification: ${error}` 
    });
    setAuthTerminal(null);
    setIsAuthenticating(false);
  };

  if (!provider || !providerConfig) return null;

  const content = (
    <>
      <DialogHeader>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
            {providerConfig.icon}
          </div>
          <div>
            <DialogTitle className="text-lg">{provider.name}</DialogTitle>
            <DialogDescription className="text-sm">
              {providerConfig.description}
            </DialogDescription>
          </div>
        </div>
      </DialogHeader>

      {(supportsOAuth || supportsGitHubCopilot) ? (
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'api' | 'oauth' | 'github-copilot')}>
          <TabsList className="w-full justify-start">
            <TabsTrigger value="api" className="flex items-center gap-2">
              <Key className="w-4 h-4" />
              {t('sections.accounts.form.apiKey')}
            </TabsTrigger>
            {supportsOAuth && (
              <TabsTrigger value="oauth" className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                {provider?.id === 'windsurf' ? 'SSO' : 'OAuth'}
              </TabsTrigger>
            )}
            {supportsGitHubCopilot && (
              <TabsTrigger value="github-copilot" className="flex items-center gap-2">
                <Github className="w-4 h-4" />
                OAuth GitHub Copilot
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="api" className="space-y-6 py-4">
            <div className="space-y-6">
              {providerConfig.requiresApiKey && provider?.id !== 'copilot' && (
                <div className="space-y-2">
                  <Label htmlFor="apiKey" className="flex items-center gap-2">
                    <Key className="w-4 h-4" />
                    {t('sections.accounts.form.apiKey')}
                  </Label>
                  <div className="relative">
                    <Input
                      id="apiKey"
                      type={showApiKey ? 'text' : 'password'}
                      placeholder={providerConfig.placeholder}
                      value={formData.apiKey || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, apiKey: e.target.value }))}
                      className="pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                      onClick={() => setShowApiKey(!showApiKey)}
                    >
                      {showApiKey ? <X className="w-3 h-3" /> : <Key className="w-3 h-3" />}
                    </Button>
                  </div>
                </div>
              )}

              {/* GitHub Copilot Token Configuration */}
              {provider?.id === 'copilot' && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="copilot-token" className="flex items-center gap-2">
                      <Key className="w-4 h-4" />
                      {t('githubCopilot.token.label')}
                    </Label>
                    <div className="relative">
                      <Input
                        id="copilot-token"
                        type={showApiKey ? 'text' : 'password'}
                        placeholder={t('githubCopilot.token.placeholder')}
                        className="font-mono pr-10"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                        onClick={() => setShowApiKey(!showApiKey)}
                      >
                        {showApiKey ? <X className="w-3 h-3" /> : <Key className="w-3 h-3" />}
                      </Button>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {t('githubCopilot.token.description')}
                    </p>
                  </div>

                  {/* Token Actions */}
                  <div className="flex gap-2">
                    <Button>
                      {t('common.save')}
                    </Button>
                    <Button variant="outline">
                      {t('common.remove')}
                    </Button>
                  </div>

                  {/* Token Status */}
                  <Alert>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                      {t('githubCopilot.token.configured')}
                    </AlertDescription>
                  </Alert>
                </div>
              )}

              {providerConfig.apiUrl && (
                <div className="space-y-2">
                  <Label htmlFor="apiUrl" className="flex items-center gap-2">
                    <Globe className="w-4 h-4" />
                    URL de l'API
                  </Label>
                  <Input
                    id="apiUrl"
                    placeholder={providerConfig.placeholder}
                    value={formData.apiUrl || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, apiUrl: e.target.value }))}
                  />
                </div>
              )}

              {providerConfig.model && (
                <div className="space-y-2">
                  <Label htmlFor="model">Modèle par défaut</Label>
                  <Input
                    id="model"
                    placeholder="gpt-4, claude-3-sonnet, etc."
                    value={formData.model || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, model: e.target.value }))}
                  />
                </div>
              )}

              {testResult && (
                <Alert className={cn(
                  testResult.success 
                    ? 'border-green-200 bg-green-50 text-green-800' 
                    : 'border-red-200 bg-red-50 text-red-800'
                )}>
                  {testResult.success ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                  <AlertDescription>
                    {testResult.message}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </TabsContent>

          <TabsContent value="oauth" className="space-y-6 py-4">
            <div className="space-y-4">
              <div className="rounded-lg bg-muted/30 border border-border p-4">
                <p className="text-sm text-muted-foreground mb-4">
                  {provider?.id === 'windsurf' 
                    ? t('sections.accounts.providerConfig.windsurfAuth.description')
                    : t('sections.accounts.providerConfig.windsurfAuth.claudeCodeAuth')
                  }
                </p>

                {provider?.id === 'windsurf' ? (
                  <div className="space-y-4">
                    {/* Auto-detect from local Windsurf IDE */}
                    <Button
                      variant="outline"
                      className="w-full"
                      disabled={isAuthenticating}
                      onClick={async () => {
                        setIsAuthenticating(true);
                        setTestResult(null);
                        try {
                          const result = await globalThis.electronAPI.detectWindsurfToken();
                          if (result.success && result.apiKey) {
                            setWindsurfSsoToken(result.apiKey);
                            setTestResult({
                              success: true,
                              message: t('sections.accounts.providerConfig.windsurfAuth.detectSuccess', { userName: result.userName || '' })
                            });
                          } else {
                            setTestResult({
                              success: false,
                              message: result.error || t('sections.accounts.providerConfig.windsurfAuth.detectFailed')
                            });
                          }
                        } catch {
                          setTestResult({
                            success: false,
                            message: t('sections.accounts.providerConfig.windsurfAuth.detectFailed')
                          });
                        } finally {
                          setIsAuthenticating(false);
                        }
                      }}
                    >
                      {isAuthenticating ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          {t('sections.accounts.providerConfig.windsurfAuth.detecting')}
                        </>
                      ) : (
                        <>
                          <LogIn className="w-4 h-4 mr-2" />
                          {t('sections.accounts.providerConfig.windsurfAuth.detectFromIDE')}
                        </>
                      )}
                    </Button>

                    {/* Or open Windsurf login manually */}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{t('sections.accounts.providerConfig.windsurfAuth.orManual')}</span>
                      <button
                        type="button"
                        className="text-primary underline hover:no-underline"
                        onClick={() => window.open('https://windsurf.com/account', '_blank')}
                      >
                        {t('sections.accounts.providerConfig.windsurfAuth.openWindsurfLogin')}
                      </button>
                    </div>

                    {/* Auth Content */}
                    {(() => {
                      // Show save form when SSO token is available
                      if (windsurfSsoToken) {
                        return (
                          <div className="space-y-4">
                            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                              <p className="text-sm text-green-800">
                                {t('sections.accounts.providerConfig.windsurfAuth.tokenReceived')}
                              </p>
                              <p className="text-xs text-green-600 mt-1 font-mono break-all">
                                {windsurfSsoToken.substring(0, 20)}...
                              </p>
                            </div>
                            <Button
                              className="w-full"
                              disabled={!windsurfSsoToken.trim()}
                              onClick={() => {
                                if (!providerConfig?.apiKey) return;
                                const newSettings = { ...settings };
                                newSettings[providerConfig.apiKey] = windsurfSsoToken.trim();
                                newSettings[`${providerConfig.apiKey}Enabled`] = true;
                                onSettingsChange(newSettings);
                                onOpenChange(false);
                              }}
                            >
                              <CheckCircle className="w-4 h-4 mr-2" />
                              {t('sections.accounts.providerConfig.windsurfAuth.saveAndConnect')}
                            </Button>
                          </div>
                        );
                      }

                      // Show auth terminal when active
                      if (authTerminal) {
                        return (
                          <div className="rounded-lg border border-primary/30 overflow-hidden" style={{ height: '320px' }}>
                            <AuthTerminal
                              terminalId={authTerminal.terminalId}
                              configDir={authTerminal.configDir}
                              profileName={authTerminal.profileName}
                              onClose={handleAuthTerminalClose}
                              onAuthSuccess={handleAuthTerminalSuccess}
                              onAuthError={handleAuthTerminalError}
                            />
                          </div>
                        );
                      }

                      // Show default auth options
                      return (
                        <div className="space-y-4">
                          <Button
                            onClick={handleOAuthAuth}
                            disabled={isAuthenticating}
                            className="w-full"
                          >
                            {isAuthenticating ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                {t('sections.accounts.providerConfig.windsurfAuth.authenticating')}
                              </>
                            ) : (
                              <>
                                <LogIn className="w-4 h-4 mr-2" />
                                {t('sections.accounts.providerConfig.windsurfAuth.connectWithClaude')}
                              </>
                            )}
                          </Button>
                          
                          <div className="text-xs text-muted-foreground">
                            <p>{t('sections.accounts.providerConfig.windsurfAuth.terminalInstructions')}</p>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Auth Content for Anthropic/Claude OAuth */}
                    {(() => {
                      // Show auth terminal when active
                      if (authTerminal) {
                        return (
                          <div className="rounded-lg border border-primary/30 overflow-hidden" style={{ height: '320px' }}>
                            <AuthTerminal
                              terminalId={authTerminal.terminalId}
                              configDir={authTerminal.configDir}
                              profileName={authTerminal.profileName}
                              onClose={handleAuthTerminalClose}
                              onAuthSuccess={handleAuthTerminalSuccess}
                              onAuthError={handleAuthTerminalError}
                            />
                          </div>
                        );
                      }

                      // Show default auth button
                      return (
                        <div className="space-y-4">
                          <Button
                            onClick={handleOAuthAuth}
                            disabled={isAuthenticating}
                            className="w-full"
                          >
                            {isAuthenticating ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                {t('sections.accounts.providerConfig.windsurfAuth.authenticating')}
                              </>
                            ) : (
                              <>
                                <LogIn className="w-4 h-4 mr-2" />
                                {t('sections.accounts.providerConfig.windsurfAuth.connectWithClaude')}
                              </>
                            )}
                          </Button>
                          
                          <div className="text-xs text-muted-foreground">
                            <p>{t('sections.accounts.providerConfig.windsurfAuth.terminalInstructions')}</p>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}

                {testResult && (
                  <Alert className={cn(
                    testResult.success 
                      ? 'border-green-200 bg-green-50 text-green-800' 
                      : 'border-red-200 bg-red-50 text-red-800'
                  )}>
                    {testResult.success ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : (
                      <AlertCircle className="h-4 w-4" />
                    )}
                    <AlertDescription>
                      {testResult.message}
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </div>
          </TabsContent>

          {supportsGitHubCopilot && (
            <TabsContent value="github-copilot" className="space-y-6 py-4">
              <div className="space-y-4">
                <div className="rounded-lg bg-muted/30 border border-border p-4">
                  <p className="text-sm text-muted-foreground mb-4">
                    {t('settings.githubCopilot.description')}
                  </p>
                  <GitHubCopilotConfig />
                </div>
              </div>
            </TabsContent>
          )}
        </Tabs>
      ) : (
        <div className="space-y-6 py-4">
          {providerConfig.requiresApiKey && (
            <div className="space-y-2">
              <Label htmlFor="apiKey" className="flex items-center gap-2">
                <Key className="w-4 h-4" />
                {t('sections.accounts.form.apiKey')}
              </Label>
              <div className="relative">
                <Input
                  id="apiKey"
                  type={showApiKey ? 'text' : 'password'}
                  placeholder={providerConfig.placeholder}
                  value={formData.apiKey || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, apiKey: e.target.value }))}
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? <X className="w-3 h-3" /> : <Key className="w-3 h-3" />}
                </Button>
              </div>
            </div>
          )}

          {providerConfig.apiUrl && (
            <div className="space-y-2">
              <Label htmlFor="apiUrl" className="flex items-center gap-2">
                <Globe className="w-4 h-4" />
                URL de l'API
              </Label>
              <Input
                id="apiUrl"
                placeholder={providerConfig.placeholder}
                value={formData.apiUrl || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, apiUrl: e.target.value }))}
              />
            </div>
          )}

          {providerConfig.model && (
            <div className="space-y-2">
              <Label htmlFor="model">Modèle par défaut</Label>
              <Input
                id="model"
                placeholder="gpt-4, claude-3-sonnet, etc."
                value={formData.model || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, model: e.target.value }))}
              />
            </div>
          )}

          {testResult && (
            <Alert className={cn(
              testResult.success 
                ? 'border-green-200 bg-green-50 text-green-800' 
                : 'border-red-200 bg-red-50 text-red-800'
            )}>
              {testResult.success ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                <AlertCircle className="h-4 w-4" />
              )}
              <AlertDescription>
                {testResult.message}
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}

      <DialogFooter className="flex gap-2">
        {provider.isConfigured && (
          <Button
            variant="destructive"
            onClick={handleDelete}
            className="mr-auto"
          >
            Supprimer
          </Button>
        )}
        
        <div className="flex gap-2 ml-auto">
          {/* Hide Test/Save when on Windsurf SSO tab — it has its own save button */}
          {!(provider?.id === 'windsurf' && activeTab === 'oauth') && (
            <>
              <Button
                variant="outline"
                onClick={handleTest}
                disabled={
                  (activeTab === 'oauth'
                    ? false
                    : (!formData.apiKey && !formData.apiUrl))
                  || isTesting
                }
              >
                {isTesting ? 'Test...' : 'Tester'}
              </Button>
              <Button onClick={handleSave}>
                Enregistrer
              </Button>
            </>
          )}
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
        </div>
      </DialogFooter>
    </>
  );

  // Si on est dans un Sheet, retourner juste le contenu sans le Dialog
  if (useSheet) {
    return <div className="space-y-6">{content}</div>;
  }

  // Sinon, retourner le Dialog complet
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[650px]">
        {/* Hidden titles for accessibility */}
        <VisuallyHidden>
          <DialogTitle>{provider?.name}</DialogTitle>
          <DialogDescription>
            {providerConfig?.description}
          </DialogDescription>
        </VisuallyHidden>
        {content}
      </DialogContent>
    </Dialog>
  );
}
