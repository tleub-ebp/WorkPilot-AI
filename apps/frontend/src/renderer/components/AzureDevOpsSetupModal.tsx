import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Eye, EyeOff, Loader2, Radio } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import type { Project, ProjectEnvConfig } from '../../shared/types';

interface AzureDevOpsSetupModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: Project;
  onComplete: () => void;
  onSkip?: () => void;
}

export function AzureDevOpsSetupModal({
  open,
  onOpenChange,
  project,
  onComplete,
  onSkip
}: AzureDevOpsSetupModalProps) {
  const { t } = useTranslation(['dialogs', 'settings']);
  const [orgUrl, setOrgUrl] = useState('');
  const [pat, setPat] = useState('');
  const [projectName, setProjectName] = useState('');
  const [showPat, setShowPat] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;

    const loadConfig = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await window.electronAPI.getProjectEnv(project.id);
        const config = result.success ? (result.data as ProjectEnvConfig | null) : null;

        setOrgUrl(config?.azureDevOpsOrgUrl || '');
        setPat(config?.azureDevOpsPat || '');
        setProjectName(config?.azureDevOpsProject || '');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load Azure DevOps settings');
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, [open, project.id]);

  const handleSave = async () => {
    const trimmedOrgUrl = orgUrl.trim();
    const trimmedPat = pat.trim();
    const trimmedProject = projectName.trim();

    if (!trimmedOrgUrl) {
      setError(t('azureDevOpsSetup.orgUrlRequired'));
      return;
    }
    if (!trimmedPat) {
      setError(t('azureDevOpsSetup.patRequired'));
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      await window.electronAPI.updateProjectEnv(project.id, {
        azureDevOpsEnabled: true,
        azureDevOpsOrgUrl: trimmedOrgUrl,
        azureDevOpsPat: trimmedPat,
        azureDevOpsProject: trimmedProject || undefined,
        githubEnabled: false
      });
      onComplete();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save Azure DevOps settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSkip = () => {
    onSkip?.();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Radio className="h-5 w-5" />
            {t('azureDevOpsSetup.title')}
          </DialogTitle>
          <DialogDescription>
            {t('azureDevOpsSetup.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('azureDevOpsSetup.loading')}
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">
                  {t('settings:azureDevOps.orgUrlLabel')}
                </Label>
                <Input
                  type="url"
                  placeholder={t('settings:azureDevOps.orgUrlPlaceholder')}
                  value={orgUrl}
                  onChange={(e) => setOrgUrl(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">
                  {t('settings:azureDevOps.patLabel')}
                </Label>
                <div className="relative">
                  <Input
                    type={showPat ? 'text' : 'password'}
                    placeholder={t('settings:azureDevOps.patPlaceholder')}
                    value={pat}
                    onChange={(e) => setPat(e.target.value)}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPat(!showPat)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPat ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">
                  {t('settings:azureDevOps.defaultProjectLabel')}
                </Label>
                <Input
                  type="text"
                  placeholder={t('settings:azureDevOps.defaultProjectPlaceholder')}
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                />
              </div>
            </>
          )}

          {error && (
            <div className="rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          {onSkip && (
            <Button variant="outline" onClick={handleSkip} disabled={isSaving}>
              {t('azureDevOpsSetup.skip')}
            </Button>
          )}
          <Button onClick={handleSave} disabled={isSaving || isLoading}>
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('azureDevOpsSetup.saving')}
              </>
            ) : (
              t('azureDevOpsSetup.save')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
