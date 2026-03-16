import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Key, Users, CheckCircle, AlertCircle } from 'lucide-react';
import { LucideGithub } from '@/lib/icons';
import { GitHubCopilotConfig } from './GitHubCopilotConfig';
import { VisuallyHidden } from '../ui/visually-hidden';
import { cn } from '@/lib/utils';
import { getProviderFields, type ProviderConfig } from './providerConfig';
import { ApiKeyConfigContent } from './ApiKeyConfigContent';
import { OAuthAuthContent } from './OAuthAuthContent';
import { useProviderAuth } from './useProviderAuth';
import { DialogFooterActions } from './DialogFooterActions';

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
  readonly useSheet?: boolean;
  readonly onProviderActivated?: (providerId: string) => void;
}

type ActiveTab = 'api' | 'oauth' | 'github-copilot';

export function ProviderConfigDialog({
  isOpen,
  onOpenChange,
  provider,
  settings,
  onSettingsChange,
  onTest,
  useSheet = false,
  onProviderActivated
}: ProviderConfigDialogProps) {
  const { t } = useTranslation('settings');
  
  // Mémoriser providerFields pour éviter les recréations infinies
  const providerFields: Record<string, ProviderConfig> = useMemo(() => getProviderFields(t), [t]);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>('api');
  
  const {
    isAuthenticating,
    authTerminal,
    windsurfSsoToken,
    windsurfAccountInfo,
    handleOAuthAuth,
    handleAuthTerminalClose,
    handleAuthTerminalSuccess,
    handleAuthTerminalError,
    handleWindsurfDetect,
    handleWindsurfSave,
    loadWindsurfAccountInfo,
    setWindsurfAccountInfo
  } = useProviderAuth();

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
    setWindsurfAccountInfo(null);
    setActiveTab(getDefaultActiveTab(provider.id, supportsOAuth));

    // Auto-load Windsurf account info when dialog opens
    if (provider.id === 'windsurf') {
      loadWindsurfAccountInfo();
    }
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
      onProviderActivated?.(provider.id);
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
    onProviderActivated?.(provider.id);
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
                <LucideGithub className="w-4 h-4" />
                OAuth GitHub Copilot
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="api" className="space-y-6 py-4">
            <ApiKeyConfigContent
              providerConfig={providerConfig}
              providerId={provider.id}
              formData={formData}
              showApiKey={showApiKey}
              testResult={testResult}
              t={t}
              onFormDataChange={setFormData}
              onToggleShowApiKey={() => setShowApiKey(!showApiKey)}
            />
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

                <OAuthAuthContent
                  providerId={provider.id}
                  providerName={provider.name}
                  isAuthenticating={isAuthenticating}
                  authTerminal={authTerminal}
                  windsurfAccountInfo={windsurfAccountInfo}
                  windsurfSsoToken={windsurfSsoToken}
                  testResult={testResult}
                  t={t}
                  onOAuthAuth={() => handleOAuthAuth(provider.id, provider.name)}
                  onAuthTerminalClose={handleAuthTerminalClose}
                  onAuthTerminalSuccess={(email) => handleAuthTerminalSuccess(email, onSettingsChange, settings, provider.id)}
                  onAuthTerminalError={handleAuthTerminalError}
                  onWindsurfDetect={async () => {
                    const result = await handleWindsurfDetect();
                    setTestResult(result);
                  }}
                  onWindsurfSave={() => handleWindsurfSave(
                    windsurfSsoToken,
                    providerConfig,
                    onSettingsChange,
                    settings,
                    onProviderActivated,
                    provider.id,
                    onOpenChange
                  )}
                />

                {testResult && (
                  <div className="mt-4">
                    <div className={cn(
                      'p-3 rounded-lg border',
                      testResult.success 
                        ? 'border-green-200 bg-green-50 text-green-800' 
                        : 'border-red-200 bg-red-50 text-red-800'
                    )}>
                      <div className="flex items-center gap-2">
                        {testResult.success ? (
                          <CheckCircle className="h-4 w-4" />
                        ) : (
                          <AlertCircle className="h-4 w-4" />
                        )}
                        <span className="text-sm">{testResult.message}</span>
                      </div>
                    </div>
                  </div>
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
        <ApiKeyConfigContent
          providerConfig={providerConfig}
          providerId={provider.id}
          formData={formData}
          showApiKey={showApiKey}
          testResult={testResult}
          t={t}
          onFormDataChange={setFormData}
          onToggleShowApiKey={() => setShowApiKey(!showApiKey)}
        />
      )}

      <DialogFooter className="flex gap-2">
        <DialogFooterActions
          provider={provider}
          activeTab={activeTab}
          isTesting={isTesting}
          formData={formData}
          onTest={handleTest}
          onSave={handleSave}
          onDelete={handleDelete}
          onOpenChange={onOpenChange}
        />
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
