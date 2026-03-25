import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

interface AzureDevOpsRemoteConfigModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onSave: (config: { orgUrl: string; pat: string }) => void;
  readonly initialConfig?: { orgUrl?: string; pat?: string };
}

export function AzureDevOpsRemoteConfigModal({ open, onOpenChange, onSave, initialConfig }: AzureDevOpsRemoteConfigModalProps) {
  const { t } = useTranslation('dialogs');
  const [orgUrl, setOrgUrl] = useState(initialConfig?.orgUrl || '');
  const [pat, setPat] = useState(initialConfig?.pat || '');
  const [error, setError] = useState<string|null>(null);

  // Validation simple d'URL Azure DevOps
  const isValidUrl = (url: string) => /^https:\/\/dev\.azure\.com\/.+/.test(url.trim());

  const handleSave = () => {
    if (!orgUrl.trim() || !pat.trim()) {
      setError(t('azureConfig.required', 'Tous les champs sont obligatoires.'));
      return;
    }
    if (!isValidUrl(orgUrl)) {
      setError(t('azureConfig.invalidUrl', 'URL Azure DevOps invalide.'));
      return;
    }
    setError(null);
    onSave({ orgUrl: orgUrl.trim(), pat: pat.trim() });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={() => { /* noop */ }}>
      <DialogContent className="sm:max-w-2xl" onInteractOutside={e => e.preventDefault()} onEscapeKeyDown={e => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>{t('azureConfig.title', 'Configurer Azure DevOps')}</DialogTitle>
          <DialogDescription>{t('azureConfig.desc', 'Renseignez l’URL de l’organisation et le token PAT.')}</DialogDescription>
        </DialogHeader>
        <div className="py-4 space-y-4">
          <div className="space-y-2">
            <Label>{t('azureConfig.orgUrl', "URL de l’organisation")}</Label>
            <Input value={orgUrl} onChange={e => setOrgUrl(e.target.value)} placeholder={t('azureConfig.orgUrlPlaceholder', 'https://dev.azure.com/myorganisation')} />
          </div>
          <div className="space-y-2">
            <Label>{t('azureConfig.pat', 'Token PAT')}</Label>
            <Input value={pat} onChange={e => setPat(e.target.value)} placeholder={t('azureConfig.patPlaceholder', 'Personal Access Token')} type="password" />
          </div>
          {error && <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3" role="alert">{error}</div>}
        </div>
        <DialogFooter>
          <Button onClick={handleSave} disabled={!orgUrl.trim() || !pat.trim() || !isValidUrl(orgUrl)}>{t('azureConfig.save', 'Valider')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}