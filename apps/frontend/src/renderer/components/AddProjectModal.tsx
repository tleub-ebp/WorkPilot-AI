import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './ui/dialog';
import { addProject } from '@/stores/project-store';
import { useToast } from '@/hooks/use-toast';
import { AzureDevOpsRemoteConfigModal } from './AzureDevOpsRemoteConfigModal';
import { GitHubRemoteConfigModal } from './GitHubRemoteConfigModal';
import { GitSetupModal } from './GitSetupModal';
import { Radio } from 'lucide-react';
import { Github } from '@/lib/icons';

// Types explicites pour les props et états
interface AddProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onProjectAdded?: (project: any, skipped: boolean) => void | Promise<void>;
}

type RemoteType = 'github' | 'azure' | null;
type RemoteConfigType = 'github' | 'azure' | null;

interface RemoteConfig {
  githubToken?: string;
  githubRepo?: string;
  azureOrg?: string;
  azurePat?: string;
  orgUrl?: string;
  pat?: string;
  repo?: string;
  token?: string;
}

// Types pour les configs remote
interface AzureDevOpsConfig {
  orgUrl: string;
  pat: string;
}
interface GitHubConfig {
  repo: string;
  token: string;
}

export function AddProjectModal({ open, onOpenChange, onProjectAdded }: AddProjectModalProps) {
  const { t } = useTranslation('dialogs');
  const { toast } = useToast();
  const [step, setStep] = useState<number>(0);
  const [projectName, setProjectName] = useState<string>('');
  const [projectLocation, setProjectLocation] = useState<string>('');
  const [initGit, setInitGit] = useState<boolean>(true);
  const [remoteType, setRemoteType] = useState<RemoteType>(null);
  const [showRemoteConfigModal, setShowRemoteConfigModal] = useState<boolean>(false);
  const [remoteConfigType, setRemoteConfigType] = useState<RemoteConfigType>(null);
  const [remoteConfig, setRemoteConfig] = useState<RemoteConfig>({});
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [createdProject, setCreatedProject] = useState<any>(null);
  const [providerSelected, setProviderSelected] = useState<boolean>(false);
  const [showGitCommitModal, setShowGitCommitModal] = useState<boolean>(false);
  const [pendingProjectPath, setPendingProjectPath] = useState<string | null>(null);
  const [detectedProvider, setDetectedProvider] = useState<'github' | 'azure_devops' | 'unknown' | null>(null);

  // Git setup modal handlers
  const handleGitInitialized = () => {
    
    setShowGitCommitModal(false);
    setPendingProjectPath(null);
    
    try {
      onOpenChange(false);
    } catch (error) {
    }
    
    // Nettoyer tous les états pour éviter les ré-rendres
    setStep(0);
    setError(null);
  };

  // Get remote config for Git setup
  const getRemoteConfigForGitSetup = () => {
    
    if (remoteType === 'github' && (remoteConfig.githubRepo || remoteConfig.repo)) {
      const config = {
        url: `https://github.com/${remoteConfig.githubRepo || remoteConfig.repo}.git`,
        name: 'origin'
      };
      return config;
    }
    if (remoteType === 'azure' && (remoteConfig.azureOrg || remoteConfig.orgUrl)) {
      // Extract repo name from org URL or construct a default one
      const orgUrl = remoteConfig.azureOrg || remoteConfig.orgUrl || '';
      const repoName = projectName?.replace(/[^A-Za-z0-9_.-]/g, '-') || 'project';
      const config = {
        url: `${orgUrl.replace(/\/$/, '')}/_git/${repoName}`,
        name: 'origin'
      };
      return config;
    }
    return undefined;
  };

  useEffect(() => {
  }, [open]);

  useEffect(() => {
    if (open) {
      setStep(0);
      setProjectName('');
      setProjectLocation('');
      setInitGit(true);
      setRemoteType(null);
      setRemoteConfig({});
      setError(null);
      setCreatedProject(null);
      setProviderSelected(false);
      setDetectedProvider(null);
    }
  }, [open]);

  useEffect(() => {
    if (step === 1) {
      setShowRemoteConfigModal(false);
    }
  }, [step]);

  // Auto-detect repository type when project path changes
  useEffect(() => {
    const autoDetectProvider = async () => {
      
      if (projectLocation && projectName && step === 0) {
        const projectPath = `${projectLocation}/${projectName.trim()}`;
        
        try {
          // Check if it's an existing git repository
          const gitStatus = await window.electronAPI.checkGitStatus(projectPath);
          
          if (gitStatus && gitStatus.success && gitStatus.data && gitStatus.data.isGitRepo) {
            const detected = await detectRepositoryProvider(projectPath);
            
            if (detected !== 'unknown') {
              // Auto-select the detected provider
              if (detected === 'github') {
                setRemoteType('github');
              } else if (detected === 'azure_devops') {
                setRemoteType('azure');
              }
              setProviderSelected(true);
            } else {
              // Unknown provider detected, keep current selection or default to skip
              if (!providerSelected) {
                setRemoteType(null);
                setProviderSelected(true);
              }
            }
          } else {
            // No git repo, don't auto-select anything unless user already selected
            if (!providerSelected) {
              setRemoteType(null);
            }
          }
        } catch (error) {
          // Error checking, don't change user's selection
        }
      } else {
      }
    };

    autoDetectProvider();
  }, [projectLocation, projectName, step]);

  // Function to detect repository provider from existing git repository
  const detectRepositoryProvider = async (projectPath: string) => {
    
    try {
      // First try to read the .git/config file directly for more reliable detection
      const gitConfigPath = `${projectPath}/.git/config`;
      
      try {
        const result = await window.electronAPI.invoke('fileExplorer:read', gitConfigPath);
        
        if (result.success && result.data) {
          const configContent = result.data;
          
          // Parse the git config file to find remote URLs
          const urlMatches = configContent.match(/url\s*=\s*(.+)/g);
          
          if (urlMatches) {
            for (const match of urlMatches) {
              const url = match.split('=', 2)[1].trim();
              
              // Check for Azure DevOps patterns
              if (url.includes('dev.azure.com') || url.includes('visualstudio.com')) {
                setDetectedProvider('azure_devops');
                setRemoteType('azure');
                return 'azure_devops';
              }
              
              // Check for GitHub patterns
              if (url.includes('github.com')) {
                setDetectedProvider('github');
                setRemoteType('github');
                return 'github';
              }
            }
          }
        } else {
        }
      } catch (configError) {
      }
      
      // Fallback to the existing git command approach
      const gitResult = await window.electronAPI.detectRepoProvider(projectPath);
      
      if (gitResult.success && gitResult.data) {
        setDetectedProvider(gitResult.data.provider);
        // Also set the remoteType for consistency in the UI
        if (gitResult.data.provider === 'github') {
          setRemoteType('github');
        } else if (gitResult.data.provider === 'azure_devops') {
          setRemoteType('azure');
        }
        return gitResult.data.provider;
      }
    } catch (error) {
    }
    
    return 'unknown';
  };

  // Determine which provider options to show
  const shouldShowProviderOptions = () => {
    
    // If we have a detected provider and it's not unknown, only show that option
    if (detectedProvider && detectedProvider !== 'unknown') {
      const options = {
        showGithub: detectedProvider === 'github',
        showAzure: detectedProvider === 'azure_devops',
        showJira: false, // Never auto-detect Jira from git
        showSkip: true // Always allow skipping
      };
      return options;
    }
    
    // Otherwise show all options
    const options = {
      showGithub: true,
      showAzure: true,
      showJira: false,
      showSkip: true
    };
    return options;
  };

  // Rendu de la première étape
  const renderStep0 = () => (
    <>
      <DialogHeader>
        <DialogTitle>{t('addProject.createNewTitle')}</DialogTitle>
        <DialogDescription>{t('addProject.createNewSubtitle')}</DialogDescription>
      </DialogHeader>
      <div className="py-4 space-y-4">
        <div className="space-y-2">
          <Label htmlFor="project-name">{t('addProject.projectName')}</Label>
          <Input
            id="project-name"
            placeholder={t('addProject.projectNamePlaceholder')}
            value={projectName}
            onChange={e => setProjectName(e.target.value)}
            autoFocus
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="project-location">{t('addProject.location')}</Label>
          <div className="flex gap-2">
            <Input
              id="project-location"
              placeholder={t('addProject.locationPlaceholder')}
              value={projectLocation}
              onChange={e => setProjectLocation(e.target.value)}
              className="flex-1"
            />
            <Button variant="outline" type="button" onClick={async () => {
              const path = await window.electronAPI.selectDirectory();
              if (path) setProjectLocation(path);
            }}>{t('addProject.browse')}</Button>
          </div>
        </div>
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={initGit} onChange={e => setInitGit(e.target.checked)} />
            {t('addProject.gitInitYes')}
          </label>
        </div>
        <div className="space-y-2">
          <Label>{t('repoProvider.title')}</Label>
          <div className="py-2 space-y-3">
            {shouldShowProviderOptions().showGithub && (
              <button
                type="button"
                aria-pressed={remoteType === 'github'}
                onClick={() => { setRemoteType('github'); setProviderSelected(true); }}
                className={`w-full flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:bg-accent hover:border-accent transition-all duration-200 text-left ${remoteType === 'github' ? 'ring-2 ring-primary' : ''}`}
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
            )}

            {shouldShowProviderOptions().showAzure && (
              <button
                type="button"
                aria-pressed={remoteType === 'azure'}
                onClick={() => { setRemoteType('azure'); setProviderSelected(true); }}
                className={`w-full flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:bg-accent hover:border-accent transition-all duration-200 text-left ${remoteType === 'azure' ? 'ring-2 ring-info' : ''}`}
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
            )}

            {shouldShowProviderOptions().showSkip && (
              <button
                type="button"
                aria-pressed={remoteType === null}
                onClick={() => { setRemoteType(null); setProviderSelected(true); }}
                className={`w-full flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:bg-accent hover:border-accent transition-all duration-200 text-left ${remoteType === null ? 'ring-2 ring-muted' : ''}`}
              >
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-muted/10">
                  <span className="font-bold text-lg text-muted-foreground">—</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-foreground">{t('repoProvider.skip')}</h3>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    {t('repoProvider.skipDescription')}
                  </p>
                </div>
              </button>
            )}
          </div>
        </div>
        {error && <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3" role="alert">{error}</div>}
      </div>
    </>
  );

  // Rendu de l'étape résumé
  const renderStep1 = () => (
    <div className="space-y-4">
      {/* Header épuré */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold">{t('addProject.summaryTitle')}</h2>
        <p className="text-sm text-muted-foreground">
          {t('addProject.summarySubtitle')}
        </p>
      </div>

      {/* Configuration cards épurées */}
      <div className="space-y-3">
        {/* Project info card */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
              <span className="text-lg">📁</span>
            </div>
            <div className="flex-1 space-y-2">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">{t('addProject.projectInfoTitle')}</h3>
                <p className="font-medium">{projectName}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">{t('addProject.locationTitle')}</h3>
                <p className="font-mono text-sm bg-muted/50 rounded px-2 py-1 inline-block">
                  {projectLocation}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Git configuration card */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
              <span className="text-lg">🔀</span>
            </div>
            <div className="flex-1 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-muted-foreground">{t('addProject.gitLocalTitle')}</h3>
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                  initGit 
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400' 
                    : 'bg-muted text-muted-foreground'
                }`}>
                  {initGit ? t('addProject.enabled') : t('addProject.disabled')}
                </div>
              </div>
              
              {/* Remote configuration */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground">{t('addProject.remoteTitle')}</h3>
                {remoteType === 'github' && (
                  <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-muted/50">
                    <Github className="h-4 w-4" />
                    <span className="text-sm font-medium">GitHub</span>
                  </div>
                )}
                {remoteType === 'azure' && (
                  <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-muted/50">
                    <Radio className="h-4 w-4" />
                    <span className="text-sm font-medium">Azure DevOps</span>
                  </div>
                )}
                {remoteType === null && (
                  <div className="px-3 py-2 rounded-md bg-muted/30">
                    <span className="text-sm text-muted-foreground">{t('addProject.noRemoteConfigured')}</span>
                  </div>
                )}
              </div>

              {/* Remote details */}
              {remoteType === 'github' && (
                <div className="space-y-1 pl-3 border-l-2 border-border">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t('addProject.repository')} :</span>
                    <span className="font-mono text-xs">{remoteConfig.githubRepo || remoteConfig.repo}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t('addProject.token')} :</span>
                    <span className="font-mono text-xs">•••••••••</span>
                  </div>
                </div>
              )}
              {remoteType === 'azure' && (
                <div className="space-y-1 pl-3 border-l-2 border-border">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t('addProject.organization')} :</span>
                    <span className="font-mono text-xs">{remoteConfig.azureOrg || remoteConfig.orgUrl}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{t('addProject.pat')} :</span>
                    <span className="font-mono text-xs">•••••••••</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // Création effective du projet
  const handleCreate = async () => {
    if (!projectName || !projectLocation) {
      setError(t('addProject.fillRequiredFields'));
      return;
    }

    setIsCreating(true);
    setError(null);
    try {
      // Créer le dossier projet
      const result = await window.electronAPI.createProjectFolder(
        projectLocation,
        projectName.trim(),
        initGit
      );
      if (!result.success || !result.data) {
        setError(result.error || 'Failed to create project folder');
        toast({
          title: t('addProject.failedToCreateTitle', 'Erreur lors de la création'),
          description: result.error || t('addProject.failedToCreate', 'Impossible de créer le projet.'),
          variant: 'destructive',
        });
        setIsCreating(false);
        return;
      }
      // Ajoute le projet à notre store
      const project = await addProject(result.data.path);
      setCreatedProject(project);
      // Configure le remote si besoin
      if (project && remoteType === 'github') {
        await window.electronAPI.updateProjectEnv(project.id, {
          githubEnabled: true,
          githubToken: remoteConfig.githubToken || remoteConfig.token,
          githubRepo: remoteConfig.githubRepo || remoteConfig.repo,
        });
      } else if (project && remoteType === 'azure') {
        await window.electronAPI.updateProjectEnv(project.id, {
          azureDevOpsEnabled: true,
          azureDevOpsOrgUrl: remoteConfig.azureOrg || remoteConfig.orgUrl,
          azureDevOpsPat: remoteConfig.azurePat || remoteConfig.pat,
        });
      }

      // Vérifie la présence d'un commit git si git a été initialisé
      if (initGit) {
        const status = await window.electronAPI.checkGitStatus(result.data.path);
        if (status && status.success && status.data && !status.data.hasCommits && !showGitCommitModal) {
          // Finaliser le projet d'abord
          onProjectAdded?.(project, false);
          
          // Puis afficher le modal Git SEULEMENT si aucun remote n'a été configuré
          // (car si un remote est configuré, le modal Git est déjà géré par les callbacks remote)
          if (!remoteType) {
            setPendingProjectPath(result.data.path);
            setShowGitCommitModal(true);
            setIsCreating(false);
            return;
          }
        }
      }
      // Si pas de popin à afficher, afficher le toast immédiatement
      toast({
        title: t('addProject.successTitle'),
        description: t('addProject.successDescription'),
        variant: 'default',
      });
      onProjectAdded?.(project, false);
      onOpenChange(false); // FERMETURE TOTALE
    } catch (err: any) {
      setError(err instanceof Error ? err.message : t('addProject.failedToCreate'));
      toast({
        title: t('addProject.failedToCreateTitle'),
        description: err instanceof Error ? err.message : t('addProject.failedToCreate'),
        variant: 'destructive',
      });
    } finally {
      setIsCreating(false);
    }
  };

  // Navigation
  const canNext = () => {
    if (step === 0) {
      return !!projectName && !!projectLocation && providerSelected;
    }
    if (step === 1 && remoteType === 'github') return !!(remoteConfig.githubToken || remoteConfig.token) && !!(remoteConfig.githubRepo || remoteConfig.repo);
    if (step === 1 && remoteType === 'azure') return !!(remoteConfig.azureOrg || remoteConfig.orgUrl) && !!(remoteConfig.azurePat || remoteConfig.pat);
    return true;
  };

  // Rendu principal
  return (
    <>
      {open && (
        <Dialog open={open} onOpenChange={onOpenChange}>
          <DialogContent className="sm:max-w-2xl">
            {step === 0 && renderStep0()}
            {step === 1 && renderStep1()}
            <DialogFooter>
              {step > 0 && (
                <Button variant="outline" onClick={() => setStep(step - 1)} disabled={isCreating}>
                  {t('addProject.back', 'Précédent')}
                </Button>
              )}
              {step < 1 && (
                <Button onClick={async () => {
                  if (remoteType === 'github') {
                    setRemoteConfigType('github');
                    setShowRemoteConfigModal(true);
                  } else if (remoteType === 'azure') {
                    setRemoteConfigType('azure');
                    setShowRemoteConfigModal(true);
                  } else {
                    // Auto-detect repository type for existing git repositories
                    if (projectLocation && projectName) {
                      const projectPath = `${projectLocation}/${projectName.trim()}`;
                      
                      // Check if .git directory exists (indicating an existing repository)
                      try {
                        const gitStatus = await window.electronAPI.checkGitStatus(projectPath);
                        if (gitStatus && gitStatus.success && gitStatus.data && gitStatus.data.isGitRepo) {
                          const detected = await detectRepositoryProvider(projectPath);
                          if (detected === 'github') {
                            setRemoteConfigType('github');
                            setShowRemoteConfigModal(true);
                          } else if (detected === 'azure_devops') {
                            setRemoteConfigType('azure');
                            setShowRemoteConfigModal(true);
                          } else {
                            // Unknown provider, skip remote configuration
                            setStep(1);
                          }
                        } else {
                          // No git repository found, skip remote configuration
                          setStep(1);
                        }
                      } catch (error) {
                        // Error checking git status, skip remote configuration
                        setStep(1);
                      }
                    } else {
                      // No project path yet, skip remote configuration
                      setStep(1);
                    }
                  }
                }} disabled={!canNext() || isCreating}>
                  {t('addProject.next')}
                </Button>
              )}
              {step === 1 && (
                <Button onClick={handleCreate} disabled={isCreating}>
                  {isCreating ? t('addProject.creating') : t('addProject.createProject')}
                </Button>
              )}
            </DialogFooter>
            {error && <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3 mt-2" role="alert">{error}</div>}
          </DialogContent>
        </Dialog>
      )}
      {showRemoteConfigModal && (remoteConfigType === 'azure' || detectedProvider === 'azure_devops') && (
        <AzureDevOpsRemoteConfigModal
          open={showRemoteConfigModal}
          onOpenChange={setShowRemoteConfigModal}
          initialConfig={remoteConfig}
          onSave={async (config: AzureDevOpsConfig) => {
            setRemoteConfig(config);
            setShowRemoteConfigModal(false);
            if (projectLocation && projectName) {
              const projectPath = `${projectLocation}/${projectName.trim()}`;
              const status = await window.electronAPI.checkGitStatus(projectPath);

              if (status && status.success && status.data && !status.data.hasCommits && !showGitCommitModal && !pendingProjectPath) {
                setPendingProjectPath(projectPath);
                setShowGitCommitModal(true);
              } else {
                setStep(1);
              }
            } else {
              setStep(1);
            }
          }}
        />
      )}

      {showRemoteConfigModal && (remoteConfigType === 'github' || detectedProvider === 'github') && (
        <GitHubRemoteConfigModal
          open={showRemoteConfigModal}
          onOpenChange={setShowRemoteConfigModal}
          initialConfig={remoteConfig}
          onSave={async (config: GitHubConfig) => {
            setRemoteConfig(config);
            setShowRemoteConfigModal(false);
            if (projectLocation && projectName) {
              const projectPath = `${projectLocation}/${projectName.trim()}`;
              const status = await window.electronAPI.checkGitStatus(projectPath);
              if (status && status.success && status.data && !status.data.hasCommits && !showGitCommitModal && !pendingProjectPath) {
                setPendingProjectPath(projectPath);
                setShowGitCommitModal(true);
              } else {
                setStep(1);
              }
            } else {
              setStep(1);
            }
          }}
        />
      )}

      {/* Git Setup Modal */}
      {showGitCommitModal && pendingProjectPath && (
        <>
          <GitSetupModal
          open={showGitCommitModal}
          onOpenChange={(isOpen) => {
            setShowGitCommitModal(isOpen);
            if (!isOpen) {
              setPendingProjectPath(null);
            }
          }}
          project={{
            id: 'temp',
            name: projectName?.trim() || 'temp-project',
            path: pendingProjectPath,
            autoBuildPath: '',
            settings: {
              model: 'claude-3-5-sonnet-20241022',
              memoryBackend: 'file',
              linearSync: false,
              notifications: {
                onTaskComplete: true,
                onTaskFailed: true,
                onReviewNeeded: true,
                sound: true
              },
              graphitiMcpEnabled: false
            },
            createdAt: new Date(),
            updatedAt: new Date()
          }}
          gitStatus={{
            isGitRepo: true,
            hasCommits: false,
            currentBranch: 'main'
          }}
          onGitInitialized={handleGitInitialized}
          onSkip={() => {
            setShowGitCommitModal(false);
            setPendingProjectPath(null);
            setTimeout(() => {
              onOpenChange(false);
            }, 200);
          }}
          remoteConfig={getRemoteConfigForGitSetup()}
        />
        </>
      )}
    </>
  );
}
