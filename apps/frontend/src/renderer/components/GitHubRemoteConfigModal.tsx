import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

export function GitHubRemoteConfigModal({ open, onOpenChange, onSave, initialConfig }) {
  const [repo, setRepo] = useState(initialConfig?.repo || '');
  const [token, setToken] = useState(initialConfig?.token || '');
  const [error, setError] = useState(null);

  const handleSave = () => {
    if (!repo.trim() || !token.trim()) {
      setError('Tous les champs sont obligatoires.');
      return;
    }
    onSave({ repo: repo.trim(), token: token.trim() });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-2xl" onInteractOutside={e => e.preventDefault()} onEscapeKeyDown={e => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>Configurer GitHub</DialogTitle>
          <DialogDescription>Renseignez le repository et le token GitHub.</DialogDescription>
        </DialogHeader>
        <div className="py-4 space-y-4">
          <div className="space-y-2">
            <Label>Repository</Label>
            <Input value={repo} onChange={e => setRepo(e.target.value)} placeholder="user/repo" />
          </div>
          <div className="space-y-2">
            <Label>Token GitHub</Label>
            <Input value={token} onChange={e => setToken(e.target.value)} placeholder="GitHub Token" type="password" />
          </div>
          {error && <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3" role="alert">{error}</div>}
        </div>
        <DialogFooter>
          <Button onClick={handleSave} disabled={!repo.trim() || !token.trim()}>Valider</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}