import { useState, useEffect, lazy, Suspense, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { debugLog } from '@shared/utils/debug-logger';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent
} from '@dnd-kit/core';
import {
  SortableContext,
  horizontalListSortingStrategy
} from '@dnd-kit/sortable';
import {
  TooltipProvider,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui';
import { Toaster } from './components/ui/toaster';
import { Sidebar, type SidebarView } from '@/components';
import { KanbanBoard, TaskCreationWizard } from '@/components';
import { KanbanSkeleton } from '@/components/ui/KanbanSkeleton';
import { TaskDetailModal } from '@/components/task-detail';
import { AppSettingsDialog, type AppSection } from './components/settings/AppSettings';
import type { ProjectSettingsSection } from './components/settings/ProjectSettingsContent';
import { TerminalGrid } from './components/TerminalGrid';
const Roadmap = lazy(() => import('./components/Roadmap').then(m => ({ default: m.Roadmap })));
const Context = lazy(() => import('@/components/context/Context').then(m => ({ default: m.Context })));
const Ideation = lazy(() => import('@/components/ideation/Ideation').then(m => ({ default: m.Ideation })));
const Insights = lazy(() => import('./components/Insights').then(m => ({ default: m.Insights })));
import { ErrorBoundary } from './components/ui/error-boundary';
const GitHubIssues = lazy(() => import('@/components/GitHubIssues').then(m => ({ default: m.GitHubIssues })));
const GitLabIssues = lazy(() => import('./components/GitLabIssues').then(m => ({ default: m.GitLabIssues })));
const GitHubPRs = lazy(() => import('./components/github-prs').then(m => ({ default: m.GitHubPRs })));
const GitLabMergeRequests = lazy(() => import('./components/gitlab-merge-requests').then(m => ({ default: m.GitLabMergeRequests })));
const Changelog = lazy(() => import('./components/Changelog').then(m => ({ default: m.Changelog })));
const AgentTools = lazy(() => import('./components/AgentTools').then(m => ({ default: m.AgentTools })));
const Worktrees = lazy(() => import('./components/Worktrees').then(m => ({ default: m.Worktrees })));
const MigrationWizard = lazy(() => import('./components/MigrationWizard').then(m => ({ default: m.MigrationWizard })));
const VisualProgrammingInterface = lazy(() => import('./components/VisualProgrammingInterface').then(m => ({ default: m.VisualProgrammingInterface })));
const DashboardMetrics = lazy(() => import('./components/DashboardMetrics').then(m => ({ default: m.DashboardMetrics })));
const AnalyticsDashboard = lazy(() => import('./components/AnalyticsDashboard').then(m => ({ default: m.AnalyticsDashboard })));
const CodeReview = lazy(() => import('./components/CodeReview').then(m => ({ default: m.CodeReview })));
const RefactoringView = lazy(() => import('./components/RefactoringView').then(m => ({ default: m.RefactoringView })));
const DocumentationView = lazy(() => import('./components/DocumentationView').then(m => ({ default: m.DocumentationView })));
const CostEstimator = lazy(() => import('./components/CostEstimator').then(m => ({ default: m.CostEstimator })));
const SessionHistory = lazy(() => import('./components/SessionHistory').then(m => ({ default: m.SessionHistory })));
const McpMarketplace = lazy(() => import('./components/mcp-marketplace/McpMarketplace').then(m => ({ default: m.McpMarketplace })));
const MissionControlDashboard = lazy(() => import('./components/mission-control/MissionControlDashboard').then(m => ({ default: m.MissionControlDashboard })));
const AgentReplayDashboard = lazy(() => import('./components/agent-replay').then(m => ({ default: m.AgentReplayDashboard })));
import { VersionWarningModal } from './components/VersionWarningModal';
import { OnboardingWizard } from './components/onboarding';
import { GitHubSetupModal } from './components/GitHubSetupModal';
import { AzureDevOpsSetupModal } from './components/AzureDevOpsSetupModal';
import { useProjectStore, loadProjects, addProject, removeProject } from './stores/project-store';
import { useTaskStore, loadTasks } from './stores/task-store';
import { useSettingsStore, loadSettings, loadProfiles, saveActiveView, saveSettings } from './stores/settings-store';
import { useClaudeProfileStore, loadClaudeProfiles } from './stores/claude-profile-store';
import { useTerminalStore, restoreTerminalSessions } from './stores/terminal-store';
import { initializeGitHubListeners } from './stores/github';
import { initDownloadProgressListener } from './stores/download-store';
import { GlobalDownloadIndicator } from './components/GlobalDownloadIndicator';
import { useIpcListeners, useTerminalProfileChange } from '@/hooks';
import { useGlobalTerminalListeners } from './hooks/useGlobalTerminalListeners';
import { COLOR_THEMES, UI_SCALE_MIN, UI_SCALE_MAX, UI_SCALE_DEFAULT } from '@shared/constants';
import type { Task, Project, ColorTheme } from '@shared/types';
import { ProjectTabBar } from './components/ProjectTabBar';
import { ViewStateProvider } from './contexts/ViewStateContext';
import { ProviderSelector } from './components/ProviderSelector';
import { ProviderContextProvider } from './components/ProviderContext';
import { AddProjectModal } from './components/AddProjectModal';
import { AlertCircle } from 'lucide-react';
import { CommandPalette } from './components/CommandPalette';
import { KeyboardShortcutsOverlay } from './components/KeyboardShortcutsOverlay';
import { PromptOptimizerDialog } from './components/prompt-optimizer';
import { VoiceControlDialog } from './components/voice-control';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { autoDetectAndUpdateProject } from './utils/repositoryDetector';

// Version constant for version-specific warnings (e.g., reauthentication notices)
const VERSION_WARNING_275 = '2.7.5';

// Wrapper component for ProjectTabBar
interface ProjectTabBarWithContextProps {
  readonly projects: Project[];
  readonly activeProjectId: string | null;
  readonly onProjectSelect: (projectId: string) => void;
  readonly onProjectClose: (projectId: string) => void;
  readonly onAddProject: () => void;
  readonly onSettingsClick: () => void;
}

function ProjectTabBarWithContext({
                                    projects,
                                    activeProjectId,
                                    onProjectSelect,
                                    onProjectClose,
                                    onAddProject,
                                    onSettingsClick
                                  }: ProjectTabBarWithContextProps) {
  return (
      <ProjectTabBar
          projects={projects}
          activeProjectId={activeProjectId}
          onProjectSelect={onProjectSelect}
          onProjectClose={onProjectClose}
          onAddProject={onAddProject}
          onSettingsClick={onSettingsClick}
      />
  );
}

export function App() {
  // Load IPC listeners for real-time updates
  useIpcListeners();

  // Load global terminal output listeners to buffer output across project switches
  // This ensures terminal output is captured even when the terminal component is not rendered
  useGlobalTerminalListeners();

  // Handle terminal profile change events (recreate terminals on profile switch)
  useTerminalProfileChange();

  // Stores
  const projects = useProjectStore((state) => state.projects);
  const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
  const activeProjectId = useProjectStore((state) => state.activeProjectId);
  const isLoadingProjects = useProjectStore((state) => state.isLoading);
  const getProjectTabs = useProjectStore((state) => state.getProjectTabs);
  const openProjectIds = useProjectStore((state) => state.openProjectIds);
  const openProjectTab = useProjectStore((state) => state.openProjectTab);
  const setActiveProject = useProjectStore((state) => state.setActiveProject);
  const reorderTabs = useProjectStore((state) => state.reorderTabs);
  const tasks = useTaskStore((state) => state.tasks);
  const isLoadingTasks = useTaskStore((state) => state.isLoading);
  const settings = useSettingsStore((state) => state.settings);
  const settingsLoading = useSettingsStore((state) => state.isLoading);

  // API Profile state
  const profiles = useSettingsStore((state) => state.profiles);

  // Claude Profile state (OAuth)
  const claudeProfiles = useClaudeProfileStore((state) => state.profiles);

  // Initialize dialog state
  const [showInitDialog, setShowInitDialog] = useState(false);
  const [pendingProject, setPendingProject] = useState<Project | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [initSuccess, setInitSuccess] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [showAddProjectModal, setShowAddProjectModal] = useState(false);

  // GitHub setup state (shown after WorkPilot AI init)
  const [showGitHubSetup, setShowGitHubSetup] = useState(false);
  const [gitHubSetupProject, setGitHubSetupProject] = useState<Project | null>(null);

  // Repo provider setup state (GitHub vs Azure DevOps)
  const [showRepoProviderSetup, setShowRepoProviderSetup] = useState(false);
  const [repoProviderProject, setRepoProviderProject] = useState<Project | null>(null);
  const [pendingRepoProvider, setPendingRepoProvider] = useState<'github' | 'azure_devops' | null>(null);
  const [showAzureDevOpsSetup, setShowAzureDevOpsSetup] = useState(false);
  const [azureDevOpsSetupProject, setAzureDevOpsSetupProject] = useState<Project | null>(null);

  // UI State
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isNewTaskDialogOpen, setIsNewTaskDialogOpen] = useState(false);
  const [isSettingsDialogOpen, setIsSettingsDialogOpen] = useState(false);
  const [settingsInitialSection, setSettingsInitialSection] = useState<AppSection | undefined>(undefined);
  const [settingsInitialProjectSection, setSettingsInitialProjectSection] = useState<ProjectSettingsSection | undefined>(undefined);
  const [activeView, setActiveView] = useState<SidebarView>('kanban');
  const [hasRestoredView, setHasRestoredView] = useState(false);
  const isRestoringView = useRef(false);
  const [isOnboardingWizardOpen, setIsOnboardingWizardOpen] = useState(false);
  const [isVersionWarningModalOpen, setIsVersionWarningModalOpen] = useState(false);
  const [isRefreshingTasks, setIsRefreshingTasks] = useState(false);

  // Command Palette & Keyboard Shortcuts state (Features 9.4 & 9.5)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isShortcutsOverlayOpen, setIsShortcutsOverlayOpen] = useState(false);

  // Global keyboard shortcuts (Feature 9.4)
  useKeyboardShortcuts({
    onCommandPalette: () => setIsCommandPaletteOpen(true),
    onKeyboardShortcuts: () => setIsShortcutsOverlayOpen(true),
    onNewTask: () => setIsNewTaskDialogOpen(true),
    onOpenSettings: () => setIsSettingsDialogOpen(true),
    onNavigate: (view) => setActiveView(view as SidebarView),
  });

  // Sauvegarder la vue active lorsqu'elle change (mais pas lors de la restauration)
  useEffect(() => {
    if (!isRestoringView.current) {
      saveActiveView(activeView);
    }
  }, [activeView]);

  // Restaurer la vue active une seule fois au chargement initial
  useEffect(() => {
    if (!settingsLoading && !hasRestoredView && settings.activeView) {
      setHasRestoredView(true);
      isRestoringView.current = true;
      setActiveView(settings.activeView);
      // Réinitialiser le flag après un court délai pour permettre les futures sauvegardes
      setTimeout(() => {
        isRestoringView.current = false;
      }, 100);
    }
  }, [settingsLoading, settings.activeView]);

  // Remove project confirmation state
  const [showRemoveProjectDialog, setShowRemoveProjectDialog] = useState(false);
  const [removeProjectError, setRemoveProjectError] = useState<string | null>(null);
  const [projectToRemove, setProjectToRemove] = useState<Project | null>(null);

  // Setup drag sensors
  const sensors = useSensors(
      useSensor(PointerSensor, {
        activationConstraint: {
          distance: 8, // 8px movement required before drag starts
        },
      })
  );

  // Track dragging state for overlay
  const [activeDragProject, setActiveDragProject] = useState<Project | null>(null);

  // Get tabs and selected project
  const projectTabs = getProjectTabs();
  const selectedProject = projects.find((p) => p.id === (activeProjectId || selectedProjectId));

  // State global pour provider LLM actif et modèles associés
  const [providers, setProviders] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [providerModels, setProviderModels] = useState<string[]>([]);
  const [providerModelsError, setProviderModelsError] = useState<string>("");

  // Initial load
  useEffect(() => {
    loadProjects();
    loadSettings();
    loadProfiles();
    loadClaudeProfiles();
    // Initialize global GitHub listeners (PR reviews, etc.) so they persist across navigation
    initializeGitHubListeners();
    // Initialize global download progress listener for Ollama model downloads
    const cleanupDownloadListener = initDownloadProgressListener();

    return () => {
      cleanupDownloadListener();
    };
  }, []);

  const getProjectsToDetect = () => {
    if (projects.length > 0) {
      return projects;
    }
    
    if (activeProjectId) {
      return projects.filter(p => p.id === activeProjectId);
    }
    
    return [];
  };

  // Helper function to check if project should be skipped
  const shouldSkipProjectDetection = async (project: Project): Promise<boolean> => {
    // Skip if project already has a provider configured in settings
    if (project.settings?.provider) {
      return true;
    }

    // Skip if Azure DevOps or GitHub is already configured in .env
    if (project.autoBuildPath) {
      try {
        const envResult = await globalThis.electronAPI.getProjectEnv(project.id);
        if (envResult.success && envResult.data) {
          return envResult.data.azureDevOpsEnabled || envResult.data.githubEnabled;
        }
      } catch {
        // If env check fails, proceed with detection
        return false;
      }
    }

    return false;
  };

  // Helper function to detect a single project
  const detectSingleProject = async (project: Project): Promise<void> => {
    try {
      const shouldSkip = await shouldSkipProjectDetection(project);
      if (shouldSkip) {
        return;
      }

      await autoDetectAndUpdateProject(project);
    } catch (error) {
      console.error(`[App] Failed to auto-detect provider for project ${project.name}:`, error);
    }
  };

  // Helper function to detect multiple projects with delays
  const detectProjectsWithDelay = async (projectsToDetect: Project[]): Promise<void> => {
    for (const project of projectsToDetect) {
      await detectSingleProject(project);
      // Small delay between projects to avoid overwhelming the system
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  };

  // Auto-detect repository types for loaded projects
  useEffect(() => {
    if (projects.length > 0 || activeProjectId) {
      const projectsToDetect = getProjectsToDetect();
      
      if (projectsToDetect.length === 0) {
        return;
      }

      // Run detection with a small delay to ensure UI is responsive
      setTimeout(() => detectProjectsWithDelay(projectsToDetect), 500);
    }
  }, [projects.length, activeProjectId]); // Trigger when projects change or active project changes

  // Restore tab state and open tabs for loaded projects
  useEffect(() => {

    if (projects.length > 0) {
      // Check openProjectIds (persisted state) instead of projectTabs (computed)
      // to avoid race condition where projectTabs is empty before projects load
      if (openProjectIds.length === 0) {
        // No tabs persisted at all, open the first available project
        const projectToOpen = activeProjectId || selectedProjectId || projects[0].id;
        // Verify the project exists before opening
        if (projects.some(p => p.id === projectToOpen)) {
          openProjectTab(projectToOpen);
          setActiveProject(projectToOpen);
        } else {
          // Fallback to first project if stored IDs are invalid
          openProjectTab(projects[0].id);
          setActiveProject(projects[0].id);
        }
        return;
      }
      // If there's an active project but no tabs open for it, open a tab
      // Note: Use openProjectIds instead of projectTabs to avoid re-render loop
      // (projectTabs creates a new array on every render)
      if (activeProjectId && !openProjectIds.includes(activeProjectId)) {
        openProjectTab(activeProjectId);
      }
      // If there's a selected project but no active project, make it active
      else if (selectedProjectId && !activeProjectId) {
        setActiveProject(selectedProjectId);
        openProjectTab(selectedProjectId);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- projectTabs is intentionally omitted to avoid infinite re-render (computed array creates new reference each render)
  }, [projects, activeProjectId, selectedProjectId, openProjectIds, openProjectTab, setActiveProject, projectTabs.length, projectTabs.map]);

  // Track if settings have been loaded at least once
  const [settingsHaveLoaded, setSettingsHaveLoaded] = useState(false);

  // Mark settings as loaded when loading completes
  useEffect(() => {
    if (!settingsLoading && !settingsHaveLoaded) {
      setSettingsHaveLoaded(true);
    }
  }, [settingsLoading, settingsHaveLoaded]);

  // First-run detection - show onboarding wizard if not completed
  // Only check AFTER settings have been loaded from disk to avoid race condition
  useEffect(() => {
    // Check if either auth method is configured
    // API profiles: if profiles exist, auth is configured (user has gone through setup)
    const hasAPIProfileConfigured = profiles.length > 0;
    const hasOAuthConfigured = claudeProfiles.some(p =>
        p.oauthToken || (p.isDefault && p.configDir)
    );
    const hasAnyAuth = hasAPIProfileConfigured || hasOAuthConfigured;

    // Only show wizard if onboarding not completed AND no auth is configured
    if (settingsHaveLoaded &&
        settings.onboardingCompleted === false &&
        !hasAnyAuth) {
      setIsOnboardingWizardOpen(true);
    }
  }, [settingsHaveLoaded, settings.onboardingCompleted, profiles, claudeProfiles]);

  // Version 2.7.5 warning - show once to notify users about reauthentication requirement
  useEffect(() => {
    const checkVersionWarning = async () => {
      if (!settingsHaveLoaded) return;

      try {
        const version = await globalThis.electronAPI.getAppVersion();
        const seenWarnings = settings.seenVersionWarnings || [];

        // Show warning for 2.7.5 if not already seen
        if (version === VERSION_WARNING_275 && !seenWarnings.includes(VERSION_WARNING_275)) {
          setIsVersionWarningModalOpen(true);
        }
      } catch (error) {
        console.error('Failed to check version warning:', error);
      }
    };

    checkVersionWarning();
  }, [settingsHaveLoaded, settings.seenVersionWarnings]);

  // Handle version warning dismissal
  const handleVersionWarningClose = () => {
    setIsVersionWarningModalOpen(false);
    // Persist that user has seen this warning (to disk, not just in-memory)
    const seenWarnings = settings.seenVersionWarnings || [];
    if (!seenWarnings.includes(VERSION_WARNING_275)) {
      saveSettings({
        seenVersionWarnings: [...seenWarnings, VERSION_WARNING_275]
      });
    }
  };

  // Sync i18n language with settings
  const { t, i18n } = useTranslation(['dialogs', 'common']);
  useEffect(() => {
    if (settings.language && settings.language !== i18n.language) {
      i18n.changeLanguage(settings.language);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Only run when settings.language changes, not on every i18n object change
  }, [settings.language, i18n.language, i18n.changeLanguage]);

  // Sync spell check language with i18n language
  useEffect(() => {
    const syncSpellCheck = async () => {
      try {
        const result = await globalThis.electronAPI.setSpellCheckLanguages(i18n.language);
        if (!result.success) {
          console.warn('[App] Failed to set spell check language:', result.error);
        }
      } catch (error) {
        console.warn('[App] Error syncing spell check language:', error);
      }
    };

    syncSpellCheck();
  }, [i18n.language]);

  // Listen for open-app-settings events (e.g., from project settings)
  useEffect(() => {
    const handleOpenAppSettings = (event: Event) => {
      const customEvent = event as CustomEvent<AppSection>;
      const section = customEvent.detail;
      if (section) {
        setSettingsInitialSection(section);
      }
      setIsSettingsDialogOpen(true);
    };

    globalThis.addEventListener('open-app-settings', handleOpenAppSettings);
    return () => {
      globalThis.removeEventListener('open-app-settings', handleOpenAppSettings);
    };
  }, []);

  // Listen for app updates - auto-open settings to 'updates' section when update is ready
  useEffect(() => {
    // When an update is downloaded and ready to install, open settings to updates section
    const cleanupDownloaded = globalThis.electronAPI.onAppUpdateDownloaded(() => {
      console.warn('[App] Update downloaded, opening settings to updates section');
      setSettingsInitialSection('updates');
      setIsSettingsDialogOpen(true);
    });

    return () => {
      cleanupDownloaded();
    };
  }, []);

  // Reset init success flag when a selected project changes
  // This allows the init dialog to show for new/different projects
  useEffect(() => {
    setInitSuccess(false);
    setInitError(null);
  }, []);

  // Check if a selected project needs initialization (e.g., .auto-claude folder was deleted)
  useEffect(() => {
    // Don't show dialog while initialization is in progress
    if (isInitializing) return;

    // Don't reopen dialog after successful initialization
    // (project update with autoBuildPath may not have propagated yet)
    if (initSuccess) return;

    if (selectedProject && !selectedProject.autoBuildPath) {
      // Project exists but isn't initialized - show init dialog
    }
  }, [selectedProject, isInitializing, initSuccess]);

  // Global keyboard shortcut: Cmd/Ctrl+T to add project (when not on terminals view)
  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      // Skip if in input fields
      if (
          e.target instanceof HTMLInputElement ||
          e.target instanceof HTMLTextAreaElement ||
          (e.target as HTMLElement)?.isContentEditable
      ) {
        return;
      }

      // Cmd/Ctrl+T: Add new project (only when not on terminals view)
      if ((e.ctrlKey || e.metaKey) && e.key === 't' && activeView !== 'terminals') {
        e.preventDefault();
        try {
          const path = await globalThis.electronAPI.selectDirectory();
          if (path) {
            const project = await addProject(path);
            if (project) {
              openProjectTab(project.id);
              if (!project.autoBuildPath) {
                setPendingProject(project);
                setInitError(null);
                setInitSuccess(false);
                setShowInitDialog(true);
              }
            }
          }
        } catch (error) {
          console.error('Failed to add project:', error);
        }
      }
    };

    globalThis.addEventListener('keydown', handleKeyDown);
    return () => globalThis.removeEventListener('keydown', handleKeyDown);
  }, [activeView, openProjectTab]);

  // Load tasks when project changes
  useEffect(() => {
    const currentProjectId = activeProjectId || selectedProjectId;
    if (currentProjectId) {
      loadTasks(currentProjectId);
      setSelectedTask(null); // Clear selection on project change
    } else {
      useTaskStore.getState().clearTasks();
    }

    // Handle terminals on project change - DON'T destroy, just restore if needed
    // Terminals are now filtered by projectPath in TerminalGrid, so each project
    // sees only its own terminals. PTY processes stay alive across project switches.
    if (selectedProject?.path) {
      restoreTerminalSessions(selectedProject.path).catch((err) => {
        console.error('[App] Failed to restore sessions:', err);
      });
    }
  }, [activeProjectId, selectedProjectId, selectedProject?.path]);

  // Apply theme on load
  useEffect(() => {
    const root = document.documentElement;

    const applyTheme = () => {
      // Apply light/dark mode
      if (settings.theme === 'dark') {
        root.classList.add('dark');
      } else if (settings.theme === 'light') {
        root.classList.remove('dark');
      } else if (globalThis.matchMedia('(prefers-color-scheme: dark)').matches) {
        // System preference - dark mode
        root.classList.add('dark');
      } else {
        // System preference - light mode
        root.classList.remove('dark');
      }
    };

    // Apply color theme via data-theme attribute
    // Validate colorTheme against known themes, fallback to 'default' if invalid
    const validThemeIds = COLOR_THEMES.map((t) => t.id);
    const rawColorTheme = settings.colorTheme ?? 'default';
    const colorTheme: ColorTheme = validThemeIds.includes(rawColorTheme)
        ? rawColorTheme
        : 'default';

    if (colorTheme === 'default') {
      delete root.dataset.theme;
    } else {
      root.dataset.theme = colorTheme;
    }

    applyTheme();

    // Listen for system theme changes
    const mediaQuery = globalThis.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (settings.theme === 'system') {
        applyTheme();
      }
    };
    mediaQuery.addEventListener('change', handleChange);

    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, [settings.theme, settings.colorTheme]);

  // Apply UI scale
  useEffect(() => {
    const root = document.documentElement;
    const scale = settings.uiScale ?? UI_SCALE_DEFAULT;
    const clampedScale = Math.max(UI_SCALE_MIN, Math.min(UI_SCALE_MAX, scale));
    root.dataset.uiScale = clampedScale.toString();
  }, [settings.uiScale]);

  // Helper function to compare task fields
  const compareTaskFields = (selected: Task, updated: Task) => {
    const comparisons = {
      subtasks: JSON.stringify(selected.subtasks || []) !== JSON.stringify(updated.subtasks || []),
      status: selected.status !== updated.status,
      title: selected.title !== updated.title,
      description: selected.description !== updated.description,
      metadata: JSON.stringify(selected.metadata || {}) !== JSON.stringify(updated.metadata || {}),
      executionProgress: JSON.stringify(selected.executionProgress || {}) !== JSON.stringify(updated.executionProgress || {}),
      qaReport: JSON.stringify(selected.qaReport || {}) !== JSON.stringify(updated.qaReport || {}),
      reviewReason: selected.reviewReason !== updated.reviewReason,
      logs: JSON.stringify(selected.logs || []) !== JSON.stringify(updated.logs || []),
    };

    const hasChanged = Object.values(comparisons).some(Boolean);
    const changedFields = Object.entries(comparisons)
      .filter(([, changed]) => changed)
      .map(([field]) => field);

    return { hasChanged, changedFields, comparisons };
  };

  // Update selected task when tasks change (for real-time updates)
  useEffect(() => {
    if (!selectedTask) {
      debugLog('[App] No selected task to update');
      return;
    }

    const updatedTask = tasks.find(
        (t) => t.id === selectedTask.id || t.specId === selectedTask.specId
    );

    debugLog('[App] Task lookup result', {
      found: !!updatedTask,
      updatedTaskId: updatedTask?.id,
      selectedTaskId: selectedTask.id,
    });

    if (!updatedTask) {
      debugLog('[App] Updated task not found in tasks array');
      return;
    }

    const { hasChanged, changedFields } = compareTaskFields(selectedTask, updatedTask);

    debugLog('[App] Task comparison', {
      hasChanged,
      changes: changedFields,
    });

    if (hasChanged) {
      debugLog('[App] Updating selectedTask', {
        taskId: updatedTask.id,
        reason: changedFields.join(', '),
      });
      setSelectedTask(updatedTask);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Intentionally omit selectedTask object to prevent infinite re-render loop
  }, [tasks, selectedTask?.id, selectedTask?.specId, selectedTask]);

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
  };

  const handleRefreshTasks = async () => {
    const currentProjectId = activeProjectId || selectedProjectId;
    if (!currentProjectId) return;
    setIsRefreshingTasks(true);
    try {
      // Pass forceRefresh: true to invalidate cache and get fresh data from disk
      // This ensures the refresh button always shows the latest task state
      await loadTasks(currentProjectId, { forceRefresh: true });
    } finally {
      setIsRefreshingTasks(false);
    }
  };

  const handleCloseTaskDetail = () => {
    setSelectedTask(null);
  };

  const handleOpenInbuiltTerminal = (_id: string, cwd: string) => {
    // Note: _id parameter is intentionally unused - terminal ID is auto-generated by addTerminal()
    // Parameter kept for callback signature consistency with callers
    console.warn('[App] Opening inbuilt terminal:', { cwd });

    // Switch to terminals view
    setActiveView('terminals');

    // Close modal
    setSelectedTask(null);

    // Add terminal to store - this will trigger Terminal component to mount
    // which will then create the backend PTY via usePtyProcess
    // Note: TerminalGrid is always mounted (just hidden), so no need to wait
    const terminal = useTerminalStore.getState().addTerminal(cwd, selectedProject?.path);

    if (terminal) {
      console.warn('[App] Terminal added to store:', terminal.id);
    } else {
      console.error('[App] Failed to add terminal to store (max terminals reached?)');
    }
  };

  const handleAddProject = () => {
    setShowAddProjectModal(true);
  };

  const handleProjectAdded = async (project: Project, needsInit: boolean) => {
    openProjectTab(project.id);
    // Si le projet a déjà une description et un provider, il est déjà initialisé
    const alreadyInitialized = !!(project.settings?.description && project.settings?.provider);
    if (needsInit && !alreadyInitialized) {
      setPendingProject(project);
      setInitError(null);
      setInitSuccess(false);
      setShowInitDialog(true);
      return;
    }
    try {
      const envResult = await globalThis.electronAPI.getProjectEnv(project.id);
      const envConfig = envResult.success ? envResult.data : null;
      const hasProvider = !!(envConfig?.githubEnabled || envConfig?.azureDevOpsEnabled);
      if (!hasProvider) {
        setRepoProviderProject(project);
        setShowRepoProviderSetup(true);
      }
    } catch {
      setShowGitHubSetup(false);
      setGitHubSetupProject(null);
      setShowAzureDevOpsSetup(false);
      setAzureDevOpsSetupProject(null);
      setPendingRepoProvider(null);
      setRepoProviderProject(project);
      setShowRepoProviderSetup(true);
    }
  };

  const handleProjectTabSelect = (projectId: string) => {
    setActiveProject(projectId);
  };

  const handleProjectTabClose = (projectId: string) => {
    // Show the confirmation dialog before removing the project
    const project = projects.find(p => p.id === projectId);
    if (project) {
      setProjectToRemove(project);
      setShowRemoveProjectDialog(true);
    }
  };

  // Handle confirm remove project
  const handleConfirmRemoveProject = () => {
    if (projectToRemove) {
      try {
        // Clear any previous error
        setRemoveProjectError(null);
        // Remove the project from the app (files are preserved on disk for re-adding later)
        removeProject(projectToRemove.id);
        // Only clear dialog state on success
        setShowRemoveProjectDialog(false);
        setProjectToRemove(null);
      } catch (err) {
        // Log error and keep dialog open so user can retry or cancel
        console.error('[App] Failed to remove project:', err);
        // Show error in dialog
        setRemoveProjectError(
            err instanceof Error ? err.message : t('common:errors.unknownError')
        );
      }
    }
  };

  const handleCancelRemoveProject = () => {
    setShowRemoveProjectDialog(false);
    setProjectToRemove(null);
    setRemoveProjectError(null);
  };

  // Handle drag start - set the active dragged project
  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const draggedProject = projectTabs.find(p => p.id === active.id);
    if (draggedProject) {
      setActiveDragProject(draggedProject);
    }
  };

  // Handle drag end - reorder tabs if dropped over another tab
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveDragProject(null);

    if (!over) return;

    const oldIndex = projectTabs.findIndex(p => p.id === active.id);
    const newIndex = projectTabs.findIndex(p => p.id === over.id);

    if (oldIndex !== newIndex && oldIndex !== -1 && newIndex !== -1) {
      reorderTabs(oldIndex, newIndex);
    }
  };

  const handleGitHubSetupComplete = async (settings: {
    githubToken: string;
    githubRepo: string;
    mainBranch: string;
    githubAuthMethod?: 'oauth' | 'pat';
  }) => {
    if (!gitHubSetupProject) return;

    try {
      // NOTE: settings.githubToken is a GitHub access token (from gh CLI),
      // NOT a Claude Code OAuth token. They are different things:
      // - GitHub token: for GitHub API access (repo operations)
      // - Claude token: for Claude AI access (run.py, roadmap, etc.)
      // The user needs to separately authenticate with Claude using 'claude setup-token'

      // Update project env config with GitHub settings
      await globalThis.electronAPI.updateProjectEnv(gitHubSetupProject.id, {
        githubEnabled: true,
        githubToken: settings.githubToken, // GitHub token for repo access
        githubRepo: settings.githubRepo,
        githubAuthMethod: settings.githubAuthMethod, // Track how user authenticated
        azureDevOpsEnabled: false
      });

      // Update project settings with mainBranch
      await globalThis.electronAPI.updateProjectSettings(gitHubSetupProject.id, {
        mainBranch: settings.mainBranch
      });

      // Refresh projects to get updated data
      await loadProjects();
    } catch (error) {
      console.error('Failed to save GitHub settings:', error);
    }

    setShowGitHubSetup(false);
    setGitHubSetupProject(null);
    setPendingRepoProvider(null);
  };

  const handleGitHubSetupSkip = () => {
    setShowGitHubSetup(false);
    setGitHubSetupProject(null);
    setPendingRepoProvider(null);
  };

  const handleAzureDevOpsSetupComplete = async () => {
    setShowAzureDevOpsSetup(false);
    setAzureDevOpsSetupProject(null);
    setPendingRepoProvider(null);
    await loadProjects();
  };

  const handleAzureDevOpsSetupSkip = () => {
    setShowAzureDevOpsSetup(false);
    setAzureDevOpsSetupProject(null);
    setPendingRepoProvider(null);
  };
  const handleGoToTask = (taskId: string) => {
    // Switch to the kanban view
    setActiveView('kanban');
    // Find and select the task (match by id or specId)
    const task = tasks.find((t) => t.id === taskId || t.specId === taskId);
    if (task) {
      setSelectedTask(task);
    }
  };

  // Récupère la liste des providers au chargement
  useEffect(() => {
    const backendUrl = import.meta.env?.VITE_BACKEND_URL || '';
    fetch(`${backendUrl}/providers`)
        .then((res) => {
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
          }
          // Check if response is actually JSON
          const contentType = res.headers.get('content-type');
          if (!contentType?.includes('application/json')) {
            throw new Error('Response is not JSON');
          }
          return res.json();
        })
        .then((data) => {
          setProviders(data.providers || []);
          // Sélectionne automatiquement 'claude' si présent
          if (!selectedProvider && data.providers?.includes('claude')) {
            setSelectedProvider('claude');
          } else if (!selectedProvider && data.providers?.length > 0) {
            setSelectedProvider(data.providers[0]);
          }
        })
        .catch((err) => {
          // Don't log loudly if backend is not available - this is expected in some setups
          if (err.message === 'Response is not JSON') {
            console.info('[App] Backend providers API not available - running without provider management');
          } else {
            console.error('Failed to fetch providers:', err);
          }
          setProviders([]);
        });
  }, []);

  // Récupère les modèles du provider sélectionné
  useEffect(() => {
    if (!selectedProvider) {
      setProviderModels([]);
      setProviderModelsError("");
      return;
    }
    const backendUrl = import.meta.env?.VITE_BACKEND_URL || '';
    fetch(`${backendUrl}/providers/models/${selectedProvider}`)
        .then((res) => {
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
          }
          // Check if response is actually JSON
          const contentType = res.headers.get('content-type');
          if (!contentType?.includes('application/json')) {
            throw new Error('Response is not JSON');
          }
          return res.json();
        })
        .then((data) => {
          setProviderModels(data.models || []);
          setProviderModelsError(data.error || "");
        })
        .catch((err) => {
          // Don't log loudly if backend is not available - this is expected in some setups
          if (err.message === 'Response is not JSON') {
            console.info('[App] Backend providers API not available - running without provider models');
          } else {
            console.error(`Failed to fetch models for provider ${selectedProvider}:`, err);
          }
          setProviderModels([]);
          setProviderModelsError(`Erreur lors de la récupération des modèles pour le provider «${selectedProvider}».`);
        });
  }, [selectedProvider]);

  const getKanbanContent = () => {
    if (isLoadingTasks && tasks.length === 0) {
      return <KanbanSkeleton />;
    }
    
    if (isRefreshingTasks) {
      return <KanbanSkeleton showRefreshText={true} />;
    }
    
    return (
      <KanbanBoard
          tasks={tasks}
          onTaskClick={handleTaskClick}
          onNewTaskClick={() => setIsNewTaskDialogOpen(true)}
          onRefresh={handleRefreshTasks}
          isRefreshing={isRefreshingTasks}
          onOpenJiraSettings={() => {
            setSettingsInitialProjectSection('jira');
            setIsSettingsDialogOpen(true);
          }}
          onOpenAzureDevOpsSettings={() => {
            setSettingsInitialProjectSection('azure-devops');
            setIsSettingsDialogOpen(true);
          }}
      />
    );
  };

  return (
      <ProviderContextProvider>
        <ViewStateProvider>
          <>
            <TooltipProvider>
              <div className="flex h-screen bg-background">
                {/* Sidebar */}
                <Sidebar
                    onSettingsClick={() => setIsSettingsDialogOpen(true)}
                    onNewTaskClick={() => setIsNewTaskDialogOpen(true)}
                    activeView={activeView}
                    onViewChange={setActiveView}
                />

                {/* Main content */}
                <div className="flex flex-1 flex-col overflow-hidden">
                  {/* Ligne sticky avec ProviderSelector et bouton "Claude Code" placée juste sous les tabs projets */}
                  <div className="flex items-center justify-between gap-3 px-2.5 py-2 border-b border-border bg-background sticky top-0 z-30">
                    <div className="flex items-center flex-1 min-w-0">
                      {/* Espace réservé pour alignement, ou autre contenu si besoin */}
                    </div>
                    <div className="shrink-0">
                      <ProviderSelector
                          selected={selectedProvider}
                          setSelected={setSelectedProvider}
                          onOpenAccountsSettings={() => {
                            setSettingsInitialSection('accounts');
                            setIsSettingsDialogOpen(true);
                          }}
                      />
                    </div>
                  </div>

                  {/* Project Tabs */}
                  {projectTabs.length > 0 && (
                      <DndContext
                          sensors={sensors}
                          collisionDetection={closestCenter}
                          onDragStart={handleDragStart}
                          onDragEnd={handleDragEnd}
                      >
                        <SortableContext items={projectTabs.map(p => p.id)} strategy={horizontalListSortingStrategy}>
                          <ProjectTabBarWithContext
                              projects={projectTabs}
                              activeProjectId={activeProjectId}
                              onProjectSelect={handleProjectTabSelect}
                              onProjectClose={handleProjectTabClose}
                              onAddProject={handleAddProject}
                              onSettingsClick={() => setIsSettingsDialogOpen(true)}
                          />
                        </SortableContext>

                        {/* Drag overlay - shows what's being dragged */}
                        <DragOverlay>
                          {activeDragProject && (
                              <div className="flex items-center gap-2 bg-card border border-border rounded-md px-4 py-2.5 shadow-lg max-w-50">
                                <div className="w-1 h-4 bg-muted-foreground rounded-full" />
                                <span className="truncate font-medium text-sm">
                          {activeDragProject.name}
                        </span>
                              </div>
                          )}
                        </DragOverlay>
                      </DndContext>
                  )}

                  {/* Main content area */}
                  <main className="flex-1 overflow-hidden">
                    <Suspense fallback={<div className="flex items-center justify-center h-full"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>}>
                    {activeView === 'mcp-marketplace' && (
                        <McpMarketplace />
                    )}
                    {activeView === 'mission-control' && (
                        <MissionControlDashboard />
                    )}
                    {activeView === 'agent-replay' && (
                        <AgentReplayDashboard />
                    )}
                    {activeView === 'kanban' && !selectedProject && (
                              <>
                                {isLoadingProjects && projects.length === 0 ? (
                                  <KanbanSkeleton />
                                ) : (
                                  <div className="flex items-center justify-center h-full text-muted">
                                    {t('common:noProjectSelected')}
                                  </div>
                                )}
                              </>
                          )}
                    {selectedProject ? (
                        <>
                          {activeView === 'kanban' && (
                              <>
                                {getKanbanContent()}
                              </>
                          )}
                          {/* TerminalGrid is always mounted but hidden when not active to preserve terminal state */}
                          <div className={activeView === 'terminals' ? 'h-full' : 'hidden'}>
                            <TerminalGrid
                                projectPath={selectedProject?.path}
                                onNewTaskClick={() => setIsNewTaskDialogOpen(true)}
                                isActive={activeView === 'terminals'}
                            />
                          </div>
                          {activeView === 'roadmap' && (activeProjectId || selectedProjectId) && (
                              <Roadmap projectId={activeProjectId || selectedProjectId!} onGoToTask={handleGoToTask} />
                          )}
                          {activeView === 'context' && (activeProjectId || selectedProjectId) && (
                              <ErrorBoundary>
                                <Context projectId={activeProjectId || selectedProjectId!} />
                              </ErrorBoundary>
                          )}
                          {activeView === 'ideation' && (activeProjectId || selectedProjectId) && (
                              <Ideation projectId={activeProjectId || selectedProjectId!} onGoToTask={handleGoToTask} />
                          )}
                          {activeView === 'insights' && (activeProjectId || selectedProjectId) && (
                              <Insights projectId={activeProjectId || selectedProjectId!} />
                          )}
                          {activeView === 'github-issues' && (activeProjectId || selectedProjectId) && (
                              <GitHubIssues
                                  onOpenSettings={() => {
                                    setSettingsInitialProjectSection('github');
                                    setIsSettingsDialogOpen(true);
                                  }}
                                  onNavigateToTask={handleGoToTask}
                              />
                          )}
                          {activeView === 'gitlab-issues' && (activeProjectId || selectedProjectId) && (
                              <GitLabIssues
                                  onOpenSettings={() => {
                                    setSettingsInitialProjectSection('gitlab');
                                    setIsSettingsDialogOpen(true);
                                  }}
                                  onNavigateToTask={handleGoToTask}
                              />
                          )}
                          {/* GitHubPRs is always mounted but hidden when not active to preserve the review state */}
                          {(activeProjectId || selectedProjectId) && (
                              <div className={activeView === 'github-prs' ? 'h-full' : 'hidden'}>
                                <GitHubPRs
                                    onOpenSettings={() => {
                                      setSettingsInitialProjectSection('github');
                                      setIsSettingsDialogOpen(true);
                                    }}
                                    isActive={activeView === 'github-prs'}
                                />
                              </div>
                          )}
                          {activeView === 'gitlab-merge-requests' && (activeProjectId || selectedProjectId) && (
                              <GitLabMergeRequests
                                  projectId={activeProjectId || selectedProjectId!}
                                  onOpenSettings={() => {
                                    setSettingsInitialProjectSection('gitlab');
                                    setIsSettingsDialogOpen(true);
                                  }}
                              />
                          )}
                          {activeView === 'changelog' && (
                              <Changelog />
                          )}
                          {activeView === 'agent-tools' && (
                              <AgentTools />
                          )}
                          {activeView === 'worktrees' && (activeProjectId || selectedProjectId) && (
                              <Worktrees projectId={activeProjectId || selectedProjectId!} />
                          )}
                          {activeView === 'migration' && (
                              <MigrationWizard />
                          )}
                          {activeView === 'visual-programming' && (
                              <VisualProgrammingInterface />
                          )}
                          {activeView === 'dashboard' && (activeProjectId || selectedProjectId) && (
                              <DashboardMetrics projectId={activeProjectId || selectedProjectId!} />
                          )}
                          {activeView === 'analytics' && (
                              <AnalyticsDashboard />
                          )}
                          {activeView === 'code-review' && (activeProjectId || selectedProjectId) && (
                              <CodeReview projectId={activeProjectId || selectedProjectId!} />
                          )}
                          {activeView === 'refactoring' && (activeProjectId || selectedProjectId) && (
                              <RefactoringView projectId={activeProjectId || selectedProjectId!} />
                          )}
                          {activeView === 'documentation' && (activeProjectId || selectedProjectId) && (
                              <DocumentationView projectId={activeProjectId || selectedProjectId!} />
                          )}
                          {activeView === 'cost-estimator' && (activeProjectId || selectedProjectId) && (
                              <CostEstimator projectId={activeProjectId || selectedProjectId!} />
                          )}
                          {activeView === 'session-history' && (activeProjectId || selectedProjectId) && (
                              <SessionHistory projectId={activeProjectId || selectedProjectId!} />
                          )}
                        </>
                    ) : (
                        <div className="flex items-center justify-center h-full text-muted">
                          {t('common:noProjectSelected')}
                        </div>
                    )}
                    </Suspense>
                  </main>
                </div>
              </div>

              {/* Modals */}
              <TaskDetailModal
                  open={!!selectedTask}
                  task={selectedTask}
                  onOpenChange={(open) => !open && handleCloseTaskDetail()}
                  onSwitchToTerminals={() => setActiveView('terminals')}
                  onOpenInbuiltTerminal={handleOpenInbuiltTerminal}
              />

              {(activeProjectId || selectedProjectId) && (
                  <TaskCreationWizard
                      projectId={activeProjectId || selectedProjectId!}
                      open={isNewTaskDialogOpen}
                      onOpenChange={setIsNewTaskDialogOpen}
                  />
              )}

              <AppSettingsDialog
                  open={isSettingsDialogOpen}
                  onOpenChange={(open) => {
                    setIsSettingsDialogOpen(open);
                    if (!open) {
                      // Reset initial sections when the dialog closes
                      setSettingsInitialSection(undefined);
                      setSettingsInitialProjectSection(undefined);
                    }
                  }}
                  initialSection={settingsInitialSection}
                  initialProjectSection={settingsInitialProjectSection}
                  onRerunWizard={() => {
                    // Reset the onboarding state to trigger wizard
                    useSettingsStore.getState().updateSettings({ onboardingCompleted: false });
                    // Close settings dialog
                    setIsSettingsDialogOpen(false);
                    // Open onboarding wizard
                    setIsOnboardingWizardOpen(true);
                  }}
              />

              <Toaster />
              {/* Global download progress indicator - shows overall progress of all downloads */}
              <GlobalDownloadIndicator />

              {/* Command Palette (Feature 9.5) */}
              <CommandPalette
                  open={isCommandPaletteOpen}
                  onOpenChange={setIsCommandPaletteOpen}
                  onNavigate={(view) => setActiveView(view as SidebarView)}
                  onNewTask={() => setIsNewTaskDialogOpen(true)}
                  onOpenSettings={() => setIsSettingsDialogOpen(true)}
                  onOpenSettingsSection={(section) => {
                    setSettingsInitialSection(section as AppSection);
                    setIsSettingsDialogOpen(true);
                  }}
              />

              {/* Keyboard Shortcuts Overlay (Feature 9.4) */}
              <KeyboardShortcutsOverlay
                  open={isShortcutsOverlayOpen}
                  onOpenChange={setIsShortcutsOverlayOpen}
              />

              {/* AI Prompt Optimizer Dialog (Feature 9) */}
              <PromptOptimizerDialog />

              {/* Voice Control Dialog (Feature 23) */}
              <VoiceControlDialog />
            </TooltipProvider>

            {/* Onboarding wizard - shown only once at app start */}
            <OnboardingWizard
                open={isOnboardingWizardOpen}
                onOpenChange={setIsOnboardingWizardOpen}
                onOpenTaskCreator={() => {
                  setIsOnboardingWizardOpen(false);
                  setIsNewTaskDialogOpen(true);
                }}
                onOpenSettings={() => {
                  setIsOnboardingWizardOpen(false);
                  setIsSettingsDialogOpen(true);
                }}
            />

            {/* Version warning modal - shown once for reauthentication notice */}
            <VersionWarningModal
                isOpen={isVersionWarningModalOpen}
                onClose={handleVersionWarningClose}
            />

            {/* Modals spécifiques à GitHub et Azure DevOps */}
            {gitHubSetupProject && (
                <GitHubSetupModal
                    open={showGitHubSetup}
                    onOpenChange={setShowGitHubSetup}
                    onComplete={handleGitHubSetupComplete}
                    onSkip={handleGitHubSetupSkip}
                    project={gitHubSetupProject}
                />
            )}

            {/* Azure DevOps Setup Modal - configure Azure DevOps */}
            {azureDevOpsSetupProject && (
                <AzureDevOpsSetupModal
                    open={showAzureDevOpsSetup}
                    onOpenChange={setShowAzureDevOpsSetup}
                    onComplete={handleAzureDevOpsSetupComplete}
                    onSkip={handleAzureDevOpsSetupSkip}
                    project={azureDevOpsSetupProject}
                />
            )}

            <AddProjectModal
                open={showAddProjectModal}
                onOpenChange={setShowAddProjectModal}
                onProjectAdded={handleProjectAdded}
            />

            {/* Remove Project Confirmation Dialog */}
            <Dialog open={showRemoveProjectDialog} onOpenChange={(open) => {
              if (!open) handleCancelRemoveProject();
            }}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t('removeProject.title')}</DialogTitle>
                  <DialogDescription>
                    {t('removeProject.description', { projectName: projectToRemove?.name || '' })}
                  </DialogDescription>
                </DialogHeader>
                {removeProjectError && (
                    <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span>{removeProjectError}</span>
                    </div>
                )}
                <DialogFooter>
                  <Button variant="outline" onClick={handleCancelRemoveProject}>
                    {t('removeProject.cancel')}
                  </Button>
                  <Button variant="destructive" onClick={handleConfirmRemoveProject}>
                    {t('removeProject.remove')}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </>
        </ViewStateProvider>
      </ProviderContextProvider>
  );
}
