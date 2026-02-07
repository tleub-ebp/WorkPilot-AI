import { useTranslation } from 'react-i18next';
import { Github, Radio } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './ui/dialog';
import { Button } from './ui/button';
import type { Project } from '../../shared/types';

interface RepositoryProviderModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: Project;
  onSelectGitHub: () => void;
  onSelectAzureDevOps: () => void;
  onSkip?: () => void;
}

export function RepositoryProviderModal({
  open,
  onOpenChange,
  project,
  onSelectGitHub,
  onSelectAzureDevOps,
  onSkip
}: RepositoryProviderModalProps) {
  const { t } = useTranslation('dialogs');
  const projectName = (() => {
    try {
      return decodeURIComponent(project.name);
    } catch {
      return project.name.replace(/%20/g, ' ');
    }
  })();

  const handleSkip = () => {
    onSkip?.();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t('repoProvider.title')}</DialogTitle>
          <DialogDescription>
            {t('repoProvider.description', { projectName })}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-3">
          <button
            onClick={onSelectGitHub}
            className="w-full flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:bg-accent hover:border-accent transition-all duration-200 text-left"
          >
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Github className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-foreground">{t('repoProvider.githubTitle')}</h3>
              <p className="text-sm text-muted-foreground mt-0.5">
                {t('repoProvider.githubDescription')}
              </p>
            </div>
          </button>

          <button
            onClick={onSelectAzureDevOps}
            className="w-full flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:bg-accent hover:border-accent transition-all duration-200 text-left"
          >
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-info/10">
              <Radio className="h-6 w-6 text-info" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-foreground">{t('repoProvider.azureTitle')}</h3>
              <p className="text-sm text-muted-foreground mt-0.5">
                {t('repoProvider.azureDescription')}
              </p>
            </div>
          </button>
        </div>

        <DialogFooter>
          {onSkip && (
            <Button variant="outline" onClick={handleSkip}>
              {t('repoProvider.skip')}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
