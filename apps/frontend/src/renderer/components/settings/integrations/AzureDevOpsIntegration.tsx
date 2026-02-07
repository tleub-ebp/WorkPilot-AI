import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { Radio, Import, Eye, EyeOff, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Switch } from '../../ui/switch';
import { Separator } from '../../ui/separator';
import type { ProjectEnvConfig, AzureDevOpsSyncStatus } from '../../../../shared/types';

interface AzureDevOpsIntegrationProps {
  envConfig: ProjectEnvConfig | null;
  updateEnvConfig: (updates: Partial<ProjectEnvConfig>) => void;
  showAzureDevOpsPat: boolean;
  setShowAzureDevOpsPat: React.Dispatch<React.SetStateAction<boolean>>;
  azureDevOpsConnectionStatus: AzureDevOpsSyncStatus | null;
  isCheckingAzureDevOps: boolean;
  onOpenAzureDevOpsImport: () => void;
}

/**
 * Azure DevOps integration settings component.
 * Manages Azure DevOps PAT, organization URL, project configuration,
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
}: AzureDevOpsIntegrationProps) {
  const { t } = useTranslation('settings');

  if (!envConfig) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="font-normal text-foreground">
            {t('settings:azureDevOps.enableSyncLabel')}
          </Label>
          <p className="text-xs text-muted-foreground">
            {t('settings:azureDevOps.enableSyncDescription')}
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
              {t('settings:azureDevOps.orgUrlLabel')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('settings:azureDevOps.orgUrlDescription')}
            </p>
            <Input
              type="url"
              placeholder={t('settings:azureDevOps.orgUrlPlaceholder')}
              value={envConfig.azureDevOpsOrgUrl || ''}
              onChange={(e) =>
                updateEnvConfig({ azureDevOpsOrgUrl: e.target.value })
              }
            />
          </div>

          {/* Personal Access Token */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('settings:azureDevOps.patLabel')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('settings:azureDevOps.patDescriptionPrefix')}{' '}
              <a
                href="https://dev.azure.com/_usersettings/tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="text-info hover:underline"
              >
                {t('settings:azureDevOps.patLinkLabel')}
              </a>
              . {t('settings:azureDevOps.patDescriptionSuffix')}
            </p>
            <div className="relative">
              <Input
                type={showAzureDevOpsPat ? 'text' : 'password'}
                placeholder={t('settings:azureDevOps.patPlaceholder')}
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

          {/* Default Project */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('settings:azureDevOps.defaultProjectLabel')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('settings:azureDevOps.defaultProjectDescription')}
            </p>
            <Input
              type="text"
              placeholder={t('settings:azureDevOps.defaultProjectPlaceholder')}
              value={envConfig.azureDevOpsProject || ''}
              onChange={(e) =>
                updateEnvConfig({ azureDevOpsProject: e.target.value })
              }
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
    ? t('settings:azureDevOps.connectionChecking')
    : connectionStatus?.connected
      ? connectionStatus.projectName
        ? t('settings:azureDevOps.connectionConnectedProject', {
            projectName: connectionStatus.projectName,
          })
        : t('settings:azureDevOps.connectionConnected')
      : connectionStatus?.error || t('settings:azureDevOps.connectionNotConnected');

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">
            {t('settings:azureDevOps.connectionStatusTitle')}
          </p>
          <p className="text-xs text-muted-foreground">
            {statusText}
          </p>
          {connectionStatus?.connected &&
            connectionStatus.workItemCount !== undefined && (
              <p className="text-xs text-muted-foreground mt-1">
                {t('settings:azureDevOps.connectionWorkItemCount', {
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
        <Radio className="h-4 w-4 text-info mt-1 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium text-foreground mb-2">
            {t('settings:azureDevOps.importPromptTitle')}
          </p>
          <p className="text-xs text-muted-foreground mb-3">
            {t('settings:azureDevOps.importPromptDescription')}
          </p>
          <Button
            size="sm"
            variant="default"
            onClick={onOpenAzureDevOpsImport}
            className="gap-2"
          >
            <Import className="h-4 w-4" />
            {t('settings:azureDevOps.importPromptButton')}
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
          {t('settings:azureDevOps.autoSyncLabel')}
        </Label>
        <p className="text-xs text-muted-foreground">
          {t('settings:azureDevOps.autoSyncDescription')}
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
        <strong className="text-warning">{t('settings:azureDevOps.autoSyncNoteLabel')}</strong>{' '}
        {t('settings:azureDevOps.autoSyncNoteDescription')}
      </p>
    </div>
  );
}
