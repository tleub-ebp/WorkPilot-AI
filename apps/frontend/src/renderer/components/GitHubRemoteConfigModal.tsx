import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { Globe } from '@/lib/icons';

interface GitHubRemoteConfigModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onSave: (config: { repo: string; token: string }) => void;
  readonly initialConfig?: { readonly repo?: string; readonly token?: string };
}

export function GitHubRemoteConfigModal({ open, onOpenChange, onSave, initialConfig }: GitHubRemoteConfigModalProps) {
  const { t } = useTranslation('dialogs');
  const [repo, setRepo] = useState(initialConfig?.repo || '');
  const [token, setToken] = useState(initialConfig?.token || '');
  const [error, setError] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationErrors, setValidationErrors] = useState({ repo: '', token: '' });
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [connectionMessage, setConnectionMessage] = useState('');

  // Détection du type de token
  const getTokenType = (tokenString: string) => {
    if (tokenString.startsWith('github_pat_')) {
      return 'fine-grained';
    }
    if (/^(ghp_|gho_|ghu_|ghs_|ghr_)/.test(tokenString)) {
      return 'classic';
    }
    return 'unknown';
  };

  // Fonctions de validation
  const validateRepositoryFormat = (repoString: string) => {
    if (!repoString.trim()) {
      return t('githubSetup.repoRequired');
    }
    // Format attendu: owner/repo
    const repoPattern = /^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/;
    if (!repoPattern.test(repoString.trim())) {
      return t('githubSetup.repoInvalidFormat');
    }
    return '';
  };

  const validateTokenFormat = (tokenString: string) => {
    if (!tokenString.trim()) {
      return t('githubSetup.tokenRequired');
    }
    // Les tokens GitHub commencent par 'ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_' (classiques) ou 'github_pat_' (fine-grained)
    const tokenPattern = /^(ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)/;
    if (!tokenPattern.test(tokenString.trim())) {
      return t('githubSetup.tokenInvalidFormat');
    }
    return '';
  };

  // Validation en temps réel
  const handleRepoChange = (value: string) => {
    setRepo(value);
    const error = validateRepositoryFormat(value);
    setValidationErrors(prev => ({ ...prev, repo: error }));
  };

  const handleTokenChange = (value: string) => {
    setToken(value);
    const error = validateTokenFormat(value);
    setValidationErrors(prev => ({ ...prev, token: error }));
  };

  // Test de connexion GitHub
  const testConnection = async () => {
    const repoError = validateRepositoryFormat(repo);
    const tokenError = validateTokenFormat(token);
    
    if (repoError || tokenError) {
      setValidationErrors({ repo: repoError, token: tokenError });
      return;
    }

    setIsValidating(true);
    setConnectionStatus('testing');
    setConnectionMessage('');
    setError(null);

    try {
      // Utiliser l'API backend pour tester la connexion GitHub
      const result = await globalThis.electronAPI.testGitHubConnection({
        repo: repo.trim(),
        token: token.trim()
      });

      if (result.success) {
        setConnectionStatus('success');
        setConnectionMessage(t('githubSetup.connectionSuccess'));
      } else {
        setConnectionStatus('error');
        
        // Messages d'erreur spécifiques selon le type de token
        const tokenType = getTokenType(token);
        if (result.status === 403) {
          if (tokenType === 'fine-grained') {
            setConnectionMessage(t('githubSetup.fineGrainedTokenPermissionsError'));
          } else {
            setConnectionMessage(t('githubSetup.classicTokenPermissionsError'));
          }
        } else if (result.status === 404) {
          setConnectionMessage(t('githubSetup.repositoryNotFoundError'));
        } else {
          setConnectionMessage(result.error || t('githubSetup.connectionFailed'));
        }
      }
    } catch (err) {
      setConnectionStatus('error');
      console.error('GitHub connection test failed:', err);
      setConnectionMessage(t('githubSetup.networkError'));
    } finally {
      setIsValidating(false);
    }
  };

  const handleSave = () => {
    const repoError = validateRepositoryFormat(repo);
    const tokenError = validateTokenFormat(token);
    
    if (repoError || tokenError) {
      setValidationErrors({ repo: repoError, token: tokenError });
      setError(t('githubSetup.correctErrorsBeforeContinue'));
      return;
    }
    
    onSave({ repo: repo.trim(), token: token.trim() });
    onOpenChange(false);
  };

  const getStatusMessage = () => {
    if (!repo.trim() || !token.trim()) {
      return t('githubSetup.fillAllFields');
    }
    if (validationErrors.repo || validationErrors.token) {
      return t('githubSetup.fixErrorsToContinue');
    }
    if (connectionStatus === 'success') {
      return t('githubSetup.connectionVerified');
    }
    return t('githubSetup.readyToSave');
  };

  const getConnectionStatusClasses = () => {
    switch (connectionStatus) {
      case 'success':
        return 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400';
      case 'error':
        return 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400';
      default:
        return 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
    }
  };

  return (
    <Dialog open={open} onOpenChange={() => { /* noop */ }}>
      <DialogContent className="sm:max-w-2xl" onInteractOutside={e => e.preventDefault()} onEscapeKeyDown={e => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-primary" />
            {t('githubSetup.title')}
          </DialogTitle>
          <DialogDescription>
            {t('githubSetup.description')}
          </DialogDescription>
        </DialogHeader>
        <div className="py-4 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="github-repo">{t('githubSetup.repositoryLabel')}</Label>
            <Input 
              id="github-repo"
              value={repo} 
              onChange={e => handleRepoChange(e.target.value)} 
              placeholder={t('githubSetup.repositoryPlaceholder')} 
              className={validationErrors.repo ? 'border-destructive' : ''}
            />
            {validationErrors.repo && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                {validationErrors.repo}
              </div>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="github-token">{t('githubSetup.tokenLabel')}</Label>
            <Input 
              id="github-token"
              value={token} 
              onChange={e => handleTokenChange(e.target.value)} 
              placeholder={t('githubSetup.tokenPlaceholder')} 
              type="password" 
              className={validationErrors.token ? 'border-destructive' : ''}
            />
            {validationErrors.token && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                {validationErrors.token}
              </div>
            )}
          </div>

          {/* Section de test de connexion */}
          <div className="border rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-sm">{t('githubSetup.testConnection')}</h4>
                <p className="text-xs text-muted-foreground">{t('githubSetup.testConnectionDesc')}</p>
              </div>
              <Button 
                variant="outline" 
                size="sm"
                onClick={testConnection}
                disabled={isValidating || !repo.trim() || !token.trim() || !!validationErrors.repo || !!validationErrors.token}
              >
                {isValidating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {t('githubSetup.testingInProgress')}
                  </>
                ) : (
                  t('githubSetup.testConnection')
                )}
              </Button>
            </div>
            
            {/* Suggestions de permissions selon le type de token */}
            {token.trim() && !validationErrors.token && (
              <div className="text-xs text-muted-foreground bg-blue-50 dark:bg-blue-900/20 p-2 rounded">
                <div className="font-medium mb-1">
                  {getTokenType(token) === 'fine-grained' ? t('githubSetup.fineGrainedTokenTitle') : t('githubSetup.classicTokenTitle')}
                </div>
                <div>
                  {getTokenType(token) === 'fine-grained' 
                    ? t('githubSetup.fineGrainedTokenPermissions')
                    : t('githubSetup.classicTokenPermissions')
                  }
                </div>
              </div>
            )}
            
            {connectionStatus !== 'idle' && (
              <div className={`flex items-center gap-2 text-sm p-2 rounded ${getConnectionStatusClasses()}`}>
                {connectionStatus === 'success' && <CheckCircle2 className="h-4 w-4" />}
                {connectionStatus === 'error' && <AlertCircle className="h-4 w-4" />}
                {connectionStatus === 'testing' && <Loader2 className="h-4 w-4 animate-spin" />}
                {connectionMessage}
              </div>
            )}
          </div>

          {error && <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3" role="alert">{error}</div>}
        </div>
        <DialogFooter className="flex justify-between items-center">
          <div className="text-sm text-muted-foreground">
            {getStatusMessage()}
          </div>
          <Button 
            onClick={handleSave} 
            disabled={!repo.trim() || !token.trim() || !!validationErrors.repo || !!validationErrors.token}
          >
            {t('githubSetup.validate')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}