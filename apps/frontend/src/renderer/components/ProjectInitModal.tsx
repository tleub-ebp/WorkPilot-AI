import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import ProviderSelector from './ProviderSelector';
import { getProviders, CanonicalProvider } from '@shared/utils/providers';

interface ProjectInitModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectName: string;
  onConfirm: (description: string, provider: string) => void;
  onCancel: () => void;
  defaultProvider?: string;
}

export const ProjectInitModal: React.FC<ProjectInitModalProps> = ({
  open,
  onOpenChange,
  projectName,
  onConfirm,
  onCancel,
  defaultProvider = '',
}) => {
  const { t } = useTranslation('projectInitModal');
  const [description, setDescription] = useState('');
  const [selectedProvider, setSelectedProvider] = useState(defaultProvider);
  const [providers, setProviders] = useState<CanonicalProvider[]>([]);

  useEffect(() => {
    if (open) {
      setDescription('');
      getProviders().then(({ providers }) => {
        setProviders(providers);
        if (defaultProvider && providers.some(p => p.name === defaultProvider)) {
          setSelectedProvider(defaultProvider);
        } else if (providers.length > 0) {
          setSelectedProvider(providers[0].name);
        } else {
          setSelectedProvider('');
        }
      });
    }
  }, [open, defaultProvider]);

  const selectedProviderLabel = providers.find(p => p.name === selectedProvider)?.label || selectedProvider || t('none');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('title', { projectName })}</DialogTitle>
          <DialogDescription>{t('description')}</DialogDescription>
        </DialogHeader>
        <div className="py-2 space-y-4">
          <div>
            <Label htmlFor="project-description">{t('projectDescriptionLabel')}</Label>
            <Input
              id="project-description"
              placeholder={t('projectDescriptionPlaceholder')}
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
          </div>
          <div>
            <Label>{t('providerLabel')}</Label>
            <ProviderSelector selected={selectedProvider} setSelected={setSelectedProvider} />
          </div>
        </div>
        <div className="py-2">
          <div className="mb-2 font-semibold">{t('verifyConfig')}</div>
          <div className="mb-1">{t('projectNameLabel')}: <span className="font-mono">{projectName}</span></div>
          <div className="mb-1">{t('selectedModelLabel')}: <span className="font-mono">{selectedProviderLabel}</span></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>{t('cancel')}</Button>
          <Button onClick={() => onConfirm(description, selectedProvider)} disabled={!selectedProvider || !description}>
            {t('createProjectButton', { projectName })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
export default ProjectInitModal;