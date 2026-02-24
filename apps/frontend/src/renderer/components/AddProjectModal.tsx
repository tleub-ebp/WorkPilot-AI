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
import { Github, Radio, Package } from 'lucide-react';

// Types explicites pour les props et états
interface AddProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onProjectAdded?: (project: any, skipped: boolean) => void | Promise<void>;
}

type RemoteType = 'github' | 'azure' | 'jira' | null;
type RemoteConfigType = 'github' | 'azure' | 'jira' | null;

interface RemoteConfig {
  githubToken?: string;
  githubRepo?: string;
  azureOrg?: string;
  azurePat?: string;
  jiraInstanceUrl?: string;
  jiraEmail?: string;
  jiraApiToken?: string;
  jiraProjectKey?: string;
  orgUrl?: string;
  pat?: string;
  repo?: string;
  token?: string;
}

interface JiraConfig {
  instanceUrl: string;
  email: string;
  apiToken: string;
  projectKey: string;
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
      console.log('🚀 Auto-detect useEffect triggered. projectLocation:', projectLocation, 'projectName:', projectName, 'step:', step);
      
      if (projectLocation && projectName && step === 0) {
        const projectPath = `${projectLocation}/${projectName.trim()}`;
        console.log('🎯 Project path ready for detection:', projectPath);
        
        try {
          // Check if it's an existing git repository
          const gitStatus = await window.electronAPI.checkGitStatus(projectPath);
          console.log('📊 Git status result:', gitStatus);
          
          if (gitStatus && gitStatus.success && gitStatus.data && gitStatus.data.isGitRepo) {
            console.log('✅ Git repository detected, proceeding with provider detection');
            const detected = await detectRepositoryProvider(projectPath);
            console.log('🔍 Detection completed, result:', detected);
            
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
            console.log('❌ No git repository found');
            if (!providerSelected) {
              setRemoteType(null);
            }
          }
        } catch (error) {
          // Error checking, don't change user's selection
          console.error('Error auto-detecting provider:', error);
        }
      } else {
        console.log('⏸️ Auto-detect conditions not met:', { projectLocation: !!projectLocation, projectName: !!projectName, step });
      }
    };

    autoDetectProvider();
  }, [projectLocation, projectName, step]);

  // Function to detect repository provider from existing git repository
  const detectRepositoryProvider = async (projectPath: string) => {
    console.log('🔍 Detecting repository provider for:', projectPath);
    
    try {
      // First try to read the .git/config file directly for more reliable detection
      const gitConfigPath = `${projectPath}/.git/config`;
      console.log('📁 Attempting to read git config from:', gitConfigPath);
      
      try {
        const result = await window.electronAPI.invoke('fileExplorer:read', gitConfigPath);
        console.log('📄 Git config read result:', result);
        
        if (result.success && result.data) {
          const configContent = result.data;
          console.log('📝 Git config content preview:', configContent.substring(0, 200));
          
          // Parse the git config file to find remote URLs
          const urlMatches = configContent.match(/url\s*=\s*(.+)/g);
          console.log('🔗 Found URL matches:', urlMatches);
          
          if (urlMatches) {
            for (const match of urlMatches) {
              const url = match.split('=', 2)[1].trim();
              console.log('🌐 Checking URL:', url);
              
              // Check for Azure DevOps patterns
              if (url.includes('dev.azure.com') || url.includes('visualstudio.com')) {
                console.log('✅ Detected Azure DevOps repository');
                setDetectedProvider('azure_devops');
                setRemoteType('azure');
                return 'azure_devops';
              }
              
              // Check for GitHub patterns
              if (url.includes('github.com')) {
                console.log('✅ Detected GitHub repository');
                setDetectedProvider('github');
                setRemoteType('github');
                return 'github';
              }
            }
          }
        } else {
          console.log('❌ Failed to read git config:', result.error);
        }
      } catch (configError) {
        console.log('⚠️ Could not read git config file, falling back to git command:', configError);
      }
      
      // Fallback to the existing git command approach
      console.log('🔄 Using fallback git command approach');
      const gitResult = await window.electronAPI.detectRepoProvider(projectPath);
      console.log('🔧 Git command result:', gitResult);
      
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
      console.error('❌ Failed to detect repository provider:', error);
    }
    
    console.log('🤷 Unknown provider detected');
    return 'unknown';
  };

  // Determine which provider options to show
  const shouldShowProviderOptions = () => {
    console.log('🎛️ Determining provider options. detectedProvider:', detectedProvider, 'remoteType:', remoteType);
    
    // If we have a detected provider and it's not unknown, only show that option
    if (detectedProvider && detectedProvider !== 'unknown') {
      const options = {
        showGithub: detectedProvider === 'github',
        showAzure: detectedProvider === 'azure_devops',
        showJira: false, // Never auto-detect Jira from git
        showSkip: true // Always allow skipping
      };
      console.log('✨ Auto-detected provider options:', options);
      return options;
    }
    
    // Otherwise show all options
    const options = {
      showGithub: true,
      showAzure: true,
      showJira: true,
      showSkip: true
    };
    console.log('📋 Showing all provider options:', options);
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
            {t('addProject.gitInitYes', 'Initialiser git local')}
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
            
            {shouldShowProviderOptions().showJira && (
              <button
                type="button"
                aria-pressed={remoteType === 'jira'}
                onClick={() => { setRemoteType('jira'); setProviderSelected(true); }}
                className={`w-full flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:bg-accent hover:border-accent transition-all duration-200 text-left ${remoteType === 'jira' ? 'ring-2 ring-blue-600' : ''}`}
              >
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-600/10">
                  <Package className="h-6 w-6 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-foreground">Jira</h3>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    Connect to Jira for issue tracking and project management
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
                    {t('repoProvider.skipDescription', 'Ne pas connecter de fournisseur distant maintenant.')}
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
    <div className="p-4 rounded-xl bg-card shadow-lg max-w-lg mx-auto">
      <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
        <span role="img" aria-label="Résumé">📝</span> Résumé de la configuration
      </h2>
      <div className="space-y-2">
        <div><b>Nom du projet :</b> {projectName}</div>
        <div><b>Emplacement :</b> {projectLocation}</div>
        <div><b>Git local :</b> {initGit ? 'Oui' : 'Non'}</div>
        <div className="flex items-center gap-2">
          <b>Remote :</b>
          {remoteType === 'github' && <span className="flex items-center gap-1"><span className="bg-black text-white rounded px-2 py-0.5 text-xs">GitHub</span></span>}
          {remoteType === 'azure' && <span className="flex items-center gap-1"><span className="bg-blue-700 text-white rounded px-2 py-0.5 text-xs">Azure DevOps</span></span>}
          {remoteType === 'jira' && <span className="flex items-center gap-1"><span className="bg-blue-600 text-white rounded px-2 py-0.5 text-xs">Jira</span></span>}
          {remoteType === null && <span className="text-muted-foreground">Aucun</span>}
        </div>
        {remoteType === 'github' && (
          <div className="ml-4 text-sm text-muted-foreground">
            <div><b>Repository :</b> {remoteConfig.githubRepo || remoteConfig.repo}</div>
            <div><b>Token :</b> {(remoteConfig.githubToken || remoteConfig.token) ? '•••••••••' : ''}</div>
          </div>
        )}
        {remoteType === 'azure' && (
          <div className="ml-4 text-sm text-muted-foreground">
            <div><b>Organisation :</b> {remoteConfig.azureOrg || remoteConfig.orgUrl}</div>
            <div><b>PAT :</b> {(remoteConfig.azurePat || remoteConfig.pat) ? '•••••••••' : ''}</div>
          </div>
        )}
        {remoteType === 'jira' && (
          <div className="ml-4 text-sm text-muted-foreground">
            <div><b>Instance URL :</b> {remoteConfig.jiraInstanceUrl}</div>
            <div><b>Email :</b> {remoteConfig.jiraEmail}</div>
            <div><b>Project Key :</b> {remoteConfig.jiraProjectKey}</div>
          </div>
        )}
      </div>
    </div>
  );

  // Création effective du projet
  const handleCreate = async () => {
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
      } else if (project && remoteType === 'jira') {
        await window.electronAPI.updateProjectEnv(project.id, {
          jiraEnabled: true,
          jiraInstanceUrl: remoteConfig.jiraInstanceUrl,
          jiraEmail: remoteConfig.jiraEmail,
          jiraApiToken: remoteConfig.jiraApiToken,
          jiraProjectKey: remoteConfig.jiraProjectKey,
        });
      }
      // Vérifie la présence d'un commit git si git a été initialisé
      if (initGit) {
        const status = await window.electronAPI.checkGitStatus(result.data.path);
        if (status && status.success && status.data && !status.data.hasCommits && !showGitCommitModal) {
          setPendingProjectPath(result.data.path);
          setShowGitCommitModal(true);
          setIsCreating(false);
          return;
        }
      }
      // Si pas de popin à afficher, afficher le toast immédiatement
      toast({
        title: t('addProject.successTitle', 'Projet créé'),
        description: t('addProject.successDescription', 'Le projet a bien été créé et configuré.'),
        variant: 'default',
      });
      onProjectAdded?.(project, false);
      onOpenChange(false); // FERMETURE TOTALE
    } catch (err: any) {
      setError(err instanceof Error ? err.message : t('addProject.failedToCreate'));
      toast({
        title: t('addProject.failedToCreateTitle', 'Erreur lors de la création'),
        description: err instanceof Error ? err.message : t('addProject.failedToCreate', 'Impossible de créer le projet.'),
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
    if (step === 1 && remoteType === 'jira') return !!(remoteConfig.jiraInstanceUrl && remoteConfig.jiraEmail && remoteConfig.jiraApiToken && remoteConfig.jiraProjectKey);
    return true;
  };

  // Rendu principal
  return (
    <>
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
                } else if (remoteType === 'jira') {
                  // Pour Jira, on demande directement la configuration sans modal complexe
                  const instanceUrl = prompt("Jira Instance URL (ex: https://your-org.atlassian.net):");
                  const email = prompt("Jira Email:");
                  const apiToken = prompt("Jira API Token:");
                  const projectKey = prompt("Jira Project Key:");
                  
                  if (instanceUrl && email && apiToken && projectKey) {
                    setRemoteConfig({
                      jiraInstanceUrl: instanceUrl,
                      jiraEmail: email,
                      jiraApiToken: apiToken,
                      jiraProjectKey: projectKey
                    });
                    setStep(1);
                  }
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
                {t('addProject.next', 'Suivant')}
              </Button>
            )}
            {step === 1 && (
              <Button onClick={handleCreate} disabled={isCreating}>
                {isCreating ? t('addProject.creating', 'Création...') : t('addProject.createProject', 'Créer le projet')}
              </Button>
            )}
          </DialogFooter>
          {error && <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3 mt-2" role="alert">{error}</div>}
        </DialogContent>
      </Dialog>
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

              if (status && status.success && status.data && !status.data.hasCommits && !showGitCommitModal) {
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
              if (status && status.success && status.data && !status.data.hasCommits && !showGitCommitModal) {
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
    </>
  );
}
