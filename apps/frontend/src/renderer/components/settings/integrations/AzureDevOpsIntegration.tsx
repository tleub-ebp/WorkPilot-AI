import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { Radio, Import, Eye, EyeOff, Loader2, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Switch } from '../../ui/switch';
import { Separator } from '../../ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select';
import type { ProjectEnvConfig, AzureDevOpsSyncStatus, AzureDevOpsRepository } from '../../../../shared/types';

interface AzureDevOpsIntegrationProps {
  envConfig: ProjectEnvConfig | null;
  updateEnvConfig: (updates: Partial<ProjectEnvConfig>) => void;
  showAzureDevOpsPat: boolean;
  setShowAzureDevOpsPat: React.Dispatch<React.SetStateAction<boolean>>;
  azureDevOpsConnectionStatus: AzureDevOpsSyncStatus | null;
  isCheckingAzureDevOps: boolean;
  onOpenAzureDevOpsImport: () => void;
  projectId: string;
}

interface RepositorySelectProps {
  projectId: string;
  value: string | undefined;
  onChange: (value: string) => void;
  disabled?: boolean;
  t: TFunction;
}

function RepositorySelect({
  projectId,
  value,
  onChange,
  disabled,
  t,
}: RepositorySelectProps) {
  const [repositories, setRepositories] = useState<AzureDevOpsRepository[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRepositories = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await window.electronAPI.listAzureDevOpsRepositories(projectId);
      if (result.success && result.data) {
        setRepositories(result.data);
      } else {
        setError(result.error || t('azureDevOps.repositoryError'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('azureDevOps.repositoryError'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, [projectId]);

  // Auto-detect and select repository on first load
  useEffect(() => {
    const autoDetectRepository = async () => {
      if (value) {
        return;
      }
      
      try {
        const result = await window.electronAPI.detectAzureDevOpsRepository(projectId);
        
        if (result.success && result.data?.repository) {
          onChange(result.data.repository);
        } else {
        }
      } catch (err) {
      }
    };

    autoDetectRepository();
  }, [projectId, value, onChange]);

  if (error) {
    return (
      <div className="space-y-2">
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
          <p className="text-xs text-destructive">{error}</p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={fetchRepositories}
          disabled={isLoading}
          className="gap-2"
        >
          <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
          {t('azureDevOps.repositoryRefresh')}
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t('azureDevOps.repositoryLoading')}
      </div>
    );
  }

  return (
    <Select value={value || ''} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger>
        <SelectValue placeholder={t('azureDevOps.repositoryPlaceholder')} />
      </SelectTrigger>
      <SelectContent>
        {repositories.map((repo) => (
          <SelectItem key={repo.id} value={repo.name}>
            {repo.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/**
 * Azure DevOps integration settings component.
 * Manages Azure DevOps PAT, organization URL, repository configuration,
 * connection status, and import functionality.
 */
export function AzureDevOpsIntegration({
  envConfig,
  updateEnvConfig,
  showAzureDevOpsPat,
  setShowAzureDevOpsPat,
  azureDevOpsConnectionStatus,
  isCheckingAzureDevOps,
  onOpenAzureDevOpsImport,
  projectId,
}: AzureDevOpsIntegrationProps) {
  const { t } = useTranslation('settings');

  if (!envConfig) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="font-normal text-foreground">
            {t('azureDevOps.enableSyncLabel')}
          </Label>
          <p className="text-xs text-muted-foreground">
            {t('azureDevOps.enableSyncDescription')}
          </p>
        </div>
        <Switch
          checked={envConfig.azureDevOpsEnabled}
          onCheckedChange={(checked) =>
            updateEnvConfig({ azureDevOpsEnabled: checked })
          }
        />
      </div>

      {envConfig.azureDevOpsEnabled && (
        <>
          {/* Organization URL */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('azureDevOps.orgUrlLabel')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('azureDevOps.orgUrlDescription')}
            </p>
            <Input
              type="url"
              placeholder={t('azureDevOps.orgUrlPlaceholder')}
              value={envConfig.azureDevOpsOrgUrl || ''}
              onChange={(e) =>
                updateEnvConfig({ azureDevOpsOrgUrl: e.target.value })
              }
            />
          </div>

          {/* Personal Access Token */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('azureDevOps.patLabel')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('azureDevOps.patDescriptionPrefix')}{' '}
              <a
                href="https://dev.azure.com/_usersettings/tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="text-info hover:underline"
              >
                {t('azureDevOps.patLinkLabel')}
              </a>
              . {t('azureDevOps.patDescriptionSuffix')}
            </p>
            <div className="relative">
              <Input
                type={showAzureDevOpsPat ? 'text' : 'password'}
                placeholder={t('azureDevOps.patPlaceholder')}
                value={envConfig.azureDevOpsPat || ''}
                onChange={(e) =>
                  updateEnvConfig({ azureDevOpsPat: e.target.value })
                }
                className="pr-10"
              />
              <button
                type="button"
                onClick={() =>
                  setShowAzureDevOpsPat(!showAzureDevOpsPat)
                }
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showAzureDevOpsPat ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          {/* Repository */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('azureDevOps.repositoryLabel')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('azureDevOps.repositoryDescription')}
            </p>
            <RepositorySelect
              projectId={projectId}
              value={envConfig.azureDevOpsProject}
              onChange={(value) =>
                updateEnvConfig({ azureDevOpsProject: value })
              }
              t={t}
            />
          </div>

          {/* Connection Status */}
          {envConfig.azureDevOpsPat && envConfig.azureDevOpsOrgUrl && (
            <ConnectionStatus
              isChecking={isCheckingAzureDevOps}
              connectionStatus={azureDevOpsConnectionStatus}
              t={t}
            />
          )}

          {/* Import Prompt */}
          {azureDevOpsConnectionStatus?.connected && (
            <ImportTasksPrompt
              onOpenAzureDevOpsImport={onOpenAzureDevOpsImport}
              t={t}
            />
          )}

          <Separator />

          {/* Auto-Sync Toggle */}
          <AutoSyncToggle
            enabled={envConfig.azureDevOpsAutoSync || false}
            onToggle={(checked) =>
              updateEnvConfig({ azureDevOpsAutoSync: checked })
            }
            t={t}
          />

          {envConfig.azureDevOpsAutoSync && <AutoSyncInfo t={t} />}
        </>
      )}
    </div>
  );
}

interface ConnectionStatusProps {
  isChecking: boolean;
  connectionStatus: AzureDevOpsSyncStatus | null;
  t: TFunction;
}

function ConnectionStatus({
  isChecking,
  connectionStatus,
  t,
}: ConnectionStatusProps) {
  const statusText = isChecking
    ? t('azureDevOps.connectionChecking')
    : connectionStatus?.connected
      ? connectionStatus.projectName
        ? t('azureDevOps.connectionConnectedProject', {
            projectName: connectionStatus.projectName,
          })
        : t('azureDevOps.connectionConnected')
      : connectionStatus?.error || t('azureDevOps.connectionNotConnected');

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">
            {t('azureDevOps.connectionStatusTitle')}
          </p>
          <p className="text-xs text-muted-foreground">
            {statusText}
          </p>
          {connectionStatus?.connected &&
            connectionStatus.workItemCount !== undefined && (
              <p className="text-xs text-muted-foreground mt-1">
                {t('azureDevOps.connectionWorkItemCount', {
                  count: connectionStatus.workItemCount,
                })}
              </p>
            )}
        </div>
        {isChecking ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : connectionStatus?.connected ? (
          <CheckCircle2 className="h-4 w-4 text-success" />
        ) : (
          <AlertCircle className="h-4 w-4 text-warning" />
        )}
      </div>
    </div>
  );
}

interface ImportTasksPromptProps {
  onOpenAzureDevOpsImport: () => void;
  t: TFunction;
}

function ImportTasksPrompt({ onOpenAzureDevOpsImport, t }: ImportTasksPromptProps) {
  return (
    <div className="rounded-lg border border-info/30 bg-info/5 p-4">
      <div className="flex items-start gap-3">
        <Radio className="h-4 w-4 text-info mt-1 shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium text-foreground mb-2">
            {t('azureDevOps.importPromptTitle')}
          </p>
          <p className="text-xs text-muted-foreground mb-3">
            {t('azureDevOps.importPromptDescription')}
          </p>
          <Button
            size="sm"
            variant="default"
            onClick={onOpenAzureDevOpsImport}
            className="gap-2"
          >
            <Import className="h-4 w-4" />
            {t('azureDevOps.importPromptButton')}
          </Button>
        </div>
      </div>
    </div>
  );
}

interface AutoSyncToggleProps {
  enabled: boolean;
  onToggle: (checked: boolean) => void;
  t: TFunction;
}

function AutoSyncToggle({ enabled, onToggle, t }: AutoSyncToggleProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="space-y-0.5">
        <Label className="font-normal text-foreground">
          {t('azureDevOps.autoSyncLabel')}
        </Label>
        <p className="text-xs text-muted-foreground">
          {t('azureDevOps.autoSyncDescription')}
        </p>
      </div>
      <Switch checked={enabled} onCheckedChange={onToggle} />
    </div>
  );
}

function AutoSyncInfo({ t }: { t: TFunction }) {
  return (
    <div className="rounded-lg border border-warning/30 bg-warning/5 p-3">
      <p className="text-xs text-muted-foreground">
        <strong className="text-warning">{t('azureDevOps.autoSyncNoteLabel')}</strong>{' '}
        {t('azureDevOps.autoSyncNoteDescription')}
      </p>
    </div>
  );
}
