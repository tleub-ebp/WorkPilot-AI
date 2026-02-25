import React, { useState, useEffect } from 'react';
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
import { Switch } from '../ui/switch';
import { Textarea } from '../ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { AlertCircle, Key, Globe, Server, CheckCircle, X, Users, LogIn, Loader2, Github } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { AuthTerminal } from './AuthTerminal';
import { GitHubCopilotConfig } from './GitHubCopilotConfig';
import { cn } from '@/lib/utils';

interface ProviderConfigDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  provider: {
    id: string;
    name: string;
    description?: string;
    isConfigured: boolean;
  } | null;
  settings: any;
  onSettingsChange: (settings: any) => void;
  onTest?: (providerId: string) => Promise<void>;
  useSheet?: boolean; // Nouvelle prop pour savoir si on est dans un Sheet
}

interface AuthTerminalState {
  terminalId: string;
  configDir: string;
  profileName: string;
}

const providerFields: Record<string, {
  apiKey?: string;
  apiUrl?: string;
  model?: string;
  description?: string;
  requiresApiKey: boolean;
  placeholder?: string;
  icon: React.ReactNode;
}> = {
  'openai': {
    apiKey: 'globalOpenAIApiKey',
    apiUrl: 'globalOpenAIApiBaseUrl',
    model: 'globalOpenAIModel',
    description: 'Clé API OpenAI pour accéder aux modèles GPT',
    requiresApiKey: true,
    placeholder: 'sk-...',
    icon: <Key className="w-4 h-4" />
  },
  'anthropic': {
    apiKey: 'globalAnthropicApiKey',
    description: 'Clé API Anthropic pour accéder aux modèles Claude',
    requiresApiKey: true,
    placeholder: 'sk-ant-...',
    icon: <Key className="w-4 h-4" />
  },
  'claude': {
    apiKey: 'globalAnthropicApiKey',
    description: 'Clé API Anthropic pour accéder aux modèles Claude',
    requiresApiKey: true,
    placeholder: 'sk-ant-...',
    icon: <Key className="w-4 h-4" />
  },
  'gemini': {
    apiKey: 'globalGoogleDeepMindApiKey',
    description: 'Clé API Google pour accéder aux modèles Gemini',
    requiresApiKey: true,
    placeholder: 'AIza...',
    icon: <Key className="w-4 h-4" />
  },
  'google': {
    apiKey: 'globalGoogleDeepMindApiKey',
    description: 'Clé API Google pour accéder aux modèles Gemini',
    requiresApiKey: true,
    placeholder: 'AIza...',
    icon: <Key className="w-4 h-4" />
  },
  'meta-llama': {
    apiKey: 'globalMetaApiKey',
    description: 'Clé API Meta pour accéder aux modèles Llama',
    requiresApiKey: true,
    placeholder: 'META-...',
    icon: <Key className="w-4 h-4" />
  },
  'meta': {
    apiKey: 'globalMetaApiKey',
    description: 'Clé API Meta pour accéder aux modèles Llama',
    requiresApiKey: true,
    placeholder: 'META-...',
    icon: <Key className="w-4 h-4" />
  },
  'mistral': {
    apiKey: 'globalMistralApiKey',
    description: 'Clé API Mistral AI pour accéder aux modèles',
    requiresApiKey: true,
    placeholder: 'MISTRAL-...',
    icon: <Key className="w-4 h-4" />
  },
  'deepseek': {
    apiKey: 'globalDeepSeekApiKey',
    description: 'Clé API DeepSeek pour accéder aux modèles',
    requiresApiKey: true,
    placeholder: 'sk-...',
    icon: <Key className="w-4 h-4" />
  },
  'grok': {
    apiKey: 'globalGrokApiKey',
    description: 'Clé API Grok pour accéder aux modèles',
    requiresApiKey: true,
    placeholder: 'xai-...',
    icon: <Key className="w-4 h-4" />
  },
  'windsurf': {
    apiKey: 'globalWindsurfApiKey',
    description: 'Clé API Windsurf pour accéder aux modèles',
    requiresApiKey: true,
    placeholder: 'ws-...',
    icon: <Key className="w-4 h-4" />
  },
  'cursor': {
    apiKey: 'globalCursorApiKey',
    description: 'Clé API Cursor pour accéder aux modèles',
    requiresApiKey: true,
    placeholder: 'crsr-...',
    icon: <Key className="w-4 h-4" />
  },
  'azure-openai': {
    apiKey: 'globalAzureApiKey',
    apiUrl: 'globalAzureApiBaseUrl',
    description: 'Clé API Azure OpenAI et endpoint URL',
    requiresApiKey: true,
    placeholder: 'Azure API Key...',
    icon: <Server className="w-4 h-4" />
  },
  'ollama': {
    apiUrl: 'globalOllamaUrl',
    description: 'URL du serveur Ollama local',
    requiresApiKey: false,
    placeholder: 'http://localhost:11434',
    icon: <Globe className="w-4 h-4" />
  },
  'copilot': {
    apiKey: 'globalCopilotToken',
    description: 'Token GitHub Copilot pour l\'authentification',
    requiresApiKey: true,
    placeholder: 'ghp_...',
    icon: <Key className="w-4 h-4" />
  },
  'aws': {
    apiKey: 'globalAwsAccessKey',
    description: 'Clé d\'accès AWS pour Bedrock',
    requiresApiKey: true,
    placeholder: 'AKIA...',
    icon: <Server className="w-4 h-4" />
  }
};

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
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [activeTab, setActiveTab] = useState<'api' | 'oauth' | 'github-copilot'>('api');
  const [authTerminal, setAuthTerminal] = useState<AuthTerminalState | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const providerConfig = provider ? providerFields[provider.id] : null;
  const supportsOAuth = ['anthropic', 'claude'].includes(provider?.id || '');
  const supportsGitHubCopilot = provider?.id === 'copilot';

  useEffect(() => {
    if (provider && providerConfig && isOpen) {
      const initialData: Record<string, string> = {};
      
      if (providerConfig.apiKey && settings[providerConfig.apiKey]) {
        initialData.apiKey = settings[providerConfig.apiKey];
      }
      if (providerConfig.apiUrl && settings[providerConfig.apiUrl]) {
        initialData.apiUrl = settings[providerConfig.apiUrl];
      }
      if (providerConfig.model && settings[providerConfig.model]) {
        initialData.model = settings[providerConfig.model];
      }
      
      setFormData(initialData);
      setTestResult(null);
      
      // Sélectionner l'onglet par défaut selon le provider
      if (provider.id === 'copilot') {
        setActiveTab('github-copilot');
      } else if (supportsOAuth) {
        setActiveTab('oauth');
      } else {
        setActiveTab('api');
      }
    }
  }, [provider, providerConfig, settings, isOpen, supportsOAuth]);

  const handleSave = () => {
    if (!provider || !providerConfig) return;

    const newSettings = { ...settings };
    
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
    if (!provider || !onTest) return;

    setIsTesting(true);
    setTestResult(null);

    try {
      await onTest(provider.id);
      setTestResult({ success: true, message: 'Connexion réussie !' });
    } catch (error) {
      setTestResult({ 
        success: false, 
        message: 'Échec de la connexion. Vérifiez vos paramètres.' 
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleDelete = () => {
    if (!provider || !providerConfig) return;

    if (confirm('Êtes-vous sûr de vouloir supprimer la configuration de ce provider ?')) {
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

      onSettingsChange(newSettings);
      onOpenChange(false);
    }
  };

  const handleOAuthAuth = () => {
    if (!provider) return;

    const terminalId = `auth-${provider.id}-${Date.now()}`;
    const configDir = `claude-config-${provider.id}`;
    const profileName = `${provider.name}-${Date.now()}`;

    setAuthTerminal({ terminalId, configDir, profileName });
    setIsAuthenticating(true);
  };

  const handleAuthTerminalClose = () => {
    setAuthTerminal(null);
    setIsAuthenticating(false);
  };

  const handleAuthTerminalSuccess = (email?: string) => {
    setTestResult({ 
      success: true, 
      message: `Authentification réussie${email ? ` pour ${email}` : ''} !` 
    });
    setAuthTerminal(null);
    setIsAuthenticating(false);
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
              Clé API
            </TabsTrigger>
            {supportsOAuth && (
              <TabsTrigger value="oauth" className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                OAuth Claude Code
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
                    Clé API
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
                  Utilisez l'authentification OAuth Claude Code pour vous connecter facilement avec votre compte Claude.
                </p>

                {!authTerminal ? (
                  <div className="space-y-4">
                    <Button
                      onClick={handleOAuthAuth}
                      disabled={isAuthenticating}
                      className="w-full"
                    >
                      {isAuthenticating ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Authentification...
                        </>
                      ) : (
                        <>
                          <LogIn className="w-4 h-4 mr-2" />
                          Se connecter avec Claude Code
                        </>
                      )}
                    </Button>
                    
                    <div className="text-xs text-muted-foreground">
                      <p>Cela ouvrira un terminal où vous pourrez exécuter la commande `/login` pour vous authentifier.</p>
                    </div>
                  </div>
                ) : (
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
                Clé API
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
          <Button
            variant="outline"
            onClick={handleTest}
            disabled={(!formData.apiKey && !formData.apiUrl) || isTesting}
          >
            {isTesting ? 'Test...' : 'Tester'}
          </Button>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button onClick={handleSave}>
            Enregistrer
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
        {content}
      </DialogContent>
    </Dialog>
  );
}
