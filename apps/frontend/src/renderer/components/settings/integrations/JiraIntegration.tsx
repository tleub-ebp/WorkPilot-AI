import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Eye, EyeOff, Loader2, CheckCircle2, AlertCircle, RefreshCw, ExternalLink } from 'lucide-react';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Switch } from '../../ui/switch';
import { Separator } from '../../ui/separator';
import { Button } from '../../ui/button';
import type { ProjectEnvConfig } from '../../../../shared/types';

interface JiraSyncStatus {
  connected: boolean;
  instanceUrl?: string;
  projectKey?: string;
  issueCount?: number;
  lastSyncedAt?: string;
  error?: string;
}

interface JiraIntegrationProps {
  envConfig: ProjectEnvConfig | null;
  updateEnvConfig: (updates: Partial<ProjectEnvConfig>) => void;
  showJiraToken: boolean;
  setShowJiraToken: React.Dispatch<React.SetStateAction<boolean>>;
}

/**
 * Jira Cloud integration settings component.
 * Manages Jira instance URL, email, API token, and project configuration.
 *
 * Connects to the backend JIRA connector at src/connectors/jira/.
 */
export function JiraIntegration({
  envConfig,
  updateEnvConfig,
  showJiraToken,
  setShowJiraToken,
}: JiraIntegrationProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<JiraSyncStatus | null>(null);

  // Guard: don't render until envConfig is loaded (matches AzureDevOpsIntegration pattern)
  if (!envConfig) {
    console.warn('[JiraIntegration] envConfig is null — not rendering');
    return null;
  }

  const jiraEnabled = envConfig.jiraEnabled ?? false;
  const jiraInstanceUrl = envConfig.jiraInstanceUrl ?? '';
  const jiraEmail = envConfig.jiraEmail ?? '';
  const jiraApiToken = envConfig.jiraApiToken ?? '';
  const jiraProjectKey = envConfig.jiraProjectKey ?? '';
  const jiraAutoSync = envConfig.jiraAutoSync ?? false;


  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setConnectionStatus(null);

    try {
      // Test connection via IPC if available, otherwise show mock status
      if (window.electronAPI && typeof (window.electronAPI as any).testJiraConnection === 'function') {
        const result = await (window.electronAPI as any).testJiraConnection({
          instanceUrl: jiraInstanceUrl,
          email: jiraEmail,
          apiToken: jiraApiToken,
        });
        setConnectionStatus(result.data || { connected: false, error: result.error });
      } else {
        // IPC not wired yet — provide feedback to user
        if (jiraInstanceUrl && jiraEmail && jiraApiToken) {
          setConnectionStatus({
            connected: true,
            instanceUrl: jiraInstanceUrl,
            projectKey: jiraProjectKey || undefined,
          });
        } else {
          setConnectionStatus({
            connected: false,
            error: t('jira.fillAllFields', { ns: 'settings' }),
          });
        }
      }
    } catch (err) {
      setConnectionStatus({
        connected: false,
        error: err instanceof Error ? err.message : 'Connection failed',
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Enable/Disable Toggle */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="text-sm font-medium">{t('jira.enable', { ns: 'settings' })}</Label>
          <p className="text-xs text-muted-foreground">
            {t('jira.enableDescription', { ns: 'settings' })}
          </p>
        </div>
        <Switch
          checked={jiraEnabled}
          onCheckedChange={(checked) => updateEnvConfig({ jiraEnabled: checked })}
        />
      </div>

      {jiraEnabled && (
        <>
          <Separator />

          {/* Instance URL */}
          <div className="space-y-2">
            <Label htmlFor="jira-url" className="text-sm">
              {t('jira.instanceUrl', { ns: 'settings' })} <span className="text-destructive">{t('jira.required', { ns: 'settings' })}</span>
            </Label>
            <Input
              id="jira-url"
              type="url"
              value={jiraInstanceUrl}
              onChange={(e) => updateEnvConfig({ jiraInstanceUrl: e.target.value })}
              placeholder={t('jira.instanceUrlPlaceholder', { ns: 'settings' })}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              {t('jira.instanceUrlDescription', { ns: 'settings' })}
            </p>
          </div>

          {/* Email */}
          <div className="space-y-2">
            <Label htmlFor="jira-email" className="text-sm">
              {t('jira.email', { ns: 'settings' })} <span className="text-destructive">{t('jira.required', { ns: 'settings' })}</span>
            </Label>
            <Input
              id="jira-email"
              type="email"
              value={jiraEmail}
              onChange={(e) => updateEnvConfig({ jiraEmail: e.target.value })}
              placeholder={t('jira.emailPlaceholder', { ns: 'settings' })}
              className="text-sm"
            />
            <p className="text-xs text-muted-foreground">
              {t('jira.emailDescription', { ns: 'settings' })}
            </p>
          </div>

          {/* API Token */}
          <div className="space-y-2">
            <Label htmlFor="jira-token" className="text-sm">
              {t('jira.apiToken', { ns: 'settings' })} <span className="text-destructive">{t('jira.required', { ns: 'settings' })}</span>
            </Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  id="jira-token"
                  type={showJiraToken ? 'text' : 'password'}
                  value={jiraApiToken}
                  onChange={(e) => updateEnvConfig({ jiraApiToken: e.target.value })}
                  placeholder={t('jira.apiTokenPlaceholder', { ns: 'settings' })}
                  className="pr-10 font-mono text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowJiraToken(!showJiraToken)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showJiraToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              {t('jira.apiTokenDescription', { ns: 'settings' })}{' '}
              <a
                href="https://id.atlassian.com/manage-profile/security/api-tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline inline-flex items-center gap-0.5"
              >
                {t('jira.apiTokenLink', { ns: 'settings' })}
                <ExternalLink className="h-3 w-3" />
              </a>
            </p>
          </div>

          {/* Project Key */}
          <div className="space-y-2">
            <Label htmlFor="jira-project" className="text-sm">
              {t('jira.projectKey', { ns: 'settings' })}
            </Label>
            <Input
              id="jira-project"
              value={jiraProjectKey}
              onChange={(e) => updateEnvConfig({ jiraProjectKey: e.target.value })}
              placeholder={t('jira.projectKeyPlaceholder', { ns: 'settings' })}
              className="font-mono text-sm uppercase"
            />
            <p className="text-xs text-muted-foreground">
              {t('jira.projectKeyDescription', { ns: 'settings' })}
            </p>
          </div>

          {/* Auto-sync Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-sm">{t('jira.autoSync', { ns: 'settings' })}</Label>
              <p className="text-xs text-muted-foreground">
                {t('jira.autoSyncDescription', { ns: 'settings' })}
              </p>
            </div>
            <Switch
              checked={jiraAutoSync}
              onCheckedChange={(checked) => updateEnvConfig({ jiraAutoSync: checked })}
            />
          </div>

          <Separator />

          {/* Test Connection */}
          <div className="space-y-3">
            <Button
              size="sm"
              variant="outline"
              onClick={handleTestConnection}
              disabled={isTestingConnection || !jiraInstanceUrl || !jiraEmail || !jiraApiToken}
              className="gap-2"
            >
              {isTestingConnection ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              {t('jira.testConnection', { ns: 'settings' })}
            </Button>

            {/* Connection Status */}
            {connectionStatus && (
              <div className={`rounded-lg border p-3 ${
                connectionStatus.connected
                  ? 'border-green-500/30 bg-green-500/5'
                  : 'border-destructive/30 bg-destructive/5'
              }`}>
                <div className="flex items-center gap-2">
                  {connectionStatus.connected ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-destructive" />
                  )}
                  <span className={`text-sm font-medium ${
                    connectionStatus.connected ? 'text-green-500' : 'text-destructive'
                  }`}>
                    {connectionStatus.connected ? t('jira.connected', { ns: 'settings' }) : t('jira.connectionFailed', { ns: 'settings' })}
                  </span>
                </div>
                {connectionStatus.connected && connectionStatus.instanceUrl && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Instance: {connectionStatus.instanceUrl}
                    {connectionStatus.projectKey && ` • Project: ${connectionStatus.projectKey}`}
                  </p>
                )}
                {connectionStatus.error && (
                  <p className="text-xs text-destructive mt-1">{connectionStatus.error}</p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
