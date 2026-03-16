// React
import { useState, useEffect, useMemo, useRef } from 'react';

// i18n
import { useTranslation } from 'react-i18next';

// Icons
import {
  Plus,
  Settings,
  LayoutGrid,
  Terminal,
  Map,
  BookOpen,
  Lightbulb,
  Download,
  Github,
  GitlabIcon,
  GitPullRequest,
  GitMerge,
  FileText,
  Sparkles,
  GitBranch,
  HelpCircle,
  Wrench,
  PanelLeft,
  PanelLeftClose,
  BarChart3,
  FileCode2,
  Wand2,
  BookOpenCheck,
  Coins,
  History,
  ChevronRight,
  Code,
  Target,
  GitFork,
  Layers,
  Brain,
  Database,
  Mic,
  Zap,
  Shield,
  TestTube,
  WandSparkles,
  Monitor,
  Store
} from 'lucide-react';

// UI
import { Button } from './ui/button';
import { Separator } from './ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import { ScrollArea } from '@/components/ui';

// Utils
import { cn } from '@/lib/utils';

// Stores
import {
  useProjectStore
} from '@/stores/project-store';

import {
  useSettingsStore,
  saveSettings,
} from '@/stores/settings-store';

import {
  useProjectEnvStore,
  loadProjectEnvConfig,
  clearProjectEnvConfig,
} from '@/stores/project-env-store';

import {
  openTestGenerationDialog
} from '@/stores/test-generation-store';

import {
  openPromptOptimizerDialog
} from '@/stores/prompt-optimizer-store';

import {
  openCodePlaygroundDialog
} from '@/stores/code-playground-store';

import {
  openConflictPredictorDialog,
} from '@/stores/conflict-predictor-store';

import {
  openContextAwareSnippetsDialog,
} from '@/stores/context-aware-snippets-store';

import {
  openDependencySentinelDialog
} from '@/stores/dependency-sentinel-store';

import { useNaturalLanguageGitStore } from '@/stores/natural-language-git-store';

import {
  openAppEmulatorDialog
} from '@/stores/app-emulator-store';

import {
  openLearningLoopDialog
} from '@/stores/learning-loop-store';

// Modals & Components
import { AddProjectModal } from './AddProjectModal';
import { GitSetupModal } from './GitSetupModal';
import { AzureDevOpsSetupModal } from './AzureDevOpsSetupModal';
import { GitHubSetupModal } from './GitHubSetupModal';
import { RateLimitIndicator } from './RateLimitIndicator';
import { ClaudeCodeStatusBadge } from './ClaudeCodeStatusBadge';
import { CopilotCliStatusBadge } from './CopilotCliStatusBadge';
import { UpdateBanner } from './UpdateBanner';

import { TestGenerationDialog } from './test-generation/TestGenerationDialog';
import { PromptOptimizerDialog } from './prompt-optimizer/PromptOptimizerDialog';
import { CodePlaygroundDialog } from './code-playground/CodePlaygroundDialog';
import { NaturalLanguageGitDialog } from './natural-language-git/NaturalLanguageGitDialog';
import { ConflictPredictorDialog } from './conflict-predictor/ConflictPredictorDialog';
import { ContextAwareSnippetsDialog } from './context-aware-snippets/ContextAwareSnippetsDialog';
import { DependencySentinelDialog } from './dependency-sentinel/DependencySentinelDialog';
import { VoiceControlDialog } from './voice-control/VoiceControlDialog';
import { AppEmulatorDialog } from './app-emulator/AppEmulatorDialog';
import { LearningLoopDialog } from './learning-loop/LearningLoopDialog';

// Types
import type { Project, GitStatus } from '@shared/types';

export type SidebarView = 'kanban' | 'terminals' | 'roadmap' | 'context' | 'ideation' | 'github-issues' | 'gitlab-issues' | 'github-prs' | 'gitlab-merge-requests' | 'changelog' | 'insights' | 'worktrees' | 'agent-tools' | 'migration' | 'visual-programming' | 'dashboard' | 'analytics' | 'code-review' | 'refactoring' | 'documentation' | 'cost-estimator' | 'session-history' | 'voice-control' | 'test-generation' | 'prompt-optimizer' | 'code-playground' | 'dependency-sentinel' | 'natural-language-git' | 'conflict-predictor' | 'context-aware-snippets' | 'app-emulator' | 'learning-loop' | 'mcp-marketplace';

interface SidebarProps {
  readonly onSettingsClick: () => void;
  readonly onNewTaskClick: () => void;
  readonly activeView?: SidebarView;
  readonly onViewChange?: (view: SidebarView) => void;
}

interface NavItem {
  id: SidebarView;
  labelKey: string;
  icon: React.ElementType;
  shortcut?: string;
}

interface NavGroup {
  id: string;
  labelKey: string;
  icon: React.ElementType;
  items: NavItem[];
  defaultExpanded?: boolean;
}

// Navigation groups with thematic organization
const navGroups: NavGroup[] = [
  {
    id: 'core',
    labelKey: 'navigation:groups.core',
    icon: Target,
    items: [
      { id: 'kanban', labelKey: 'navigation:items.kanban', icon: LayoutGrid, shortcut: 'K' },
      { id: 'terminals', labelKey: 'navigation:items.terminals', icon: Terminal, shortcut: 'A' },
      { id: 'insights', labelKey: 'navigation:items.insights', icon: Sparkles, shortcut: 'N' },
    ],
    defaultExpanded: true
  },
  {
    id: 'development',
    labelKey: 'navigation:groups.development',
    icon: Code,
    items: [
      { id: 'code-review', labelKey: 'navigation:items.codeReview', icon: FileCode2, shortcut: 'V' },
      { id: 'refactoring', labelKey: 'navigation:items.refactoring', icon: Wand2, shortcut: 'F' },
      { id: 'documentation', labelKey: 'navigation:items.documentation', icon: BookOpenCheck, shortcut: 'O' },
      { id: 'agent-tools', labelKey: 'navigation:items.agentTools', icon: Wrench, shortcut: 'M' },
      { id: 'visual-programming', labelKey: 'navigation:items.visualProgramming', icon: Brain, shortcut: 'V' },
    ],
    defaultExpanded: false
  },
  {
    id: 'ai-tools',
    labelKey: 'navigation:groups.aiTools',
    icon: Sparkles,
    items: [
      { id: 'test-generation', labelKey: 'navigation:items.testGeneration', icon: TestTube, shortcut: 'T' },
      { id: 'prompt-optimizer', labelKey: 'navigation:items.promptOptimizer', icon: WandSparkles, shortcut: 'P' },
      { id: 'context-aware-snippets', labelKey: 'navigation:items.contextAwareSnippets', icon: Code, shortcut: 'S' },
      { id: 'code-playground', labelKey: 'navigation:items.codePlayground', icon: Zap, shortcut: 'G' },
      { id: 'dependency-sentinel', labelKey: 'navigation:items.dependencySentinel', icon: Shield, shortcut: 'D' },
      { id: 'conflict-predictor', labelKey: 'navigation:items.conflictPredictor', icon: GitMerge, shortcut: 'C' },
      { id: 'natural-language-git', labelKey: 'navigation:items.naturalLanguageGit', icon: GitBranch, shortcut: 'G' },
      { id: 'app-emulator', labelKey: 'navigation:items.appEmulator', icon: Monitor, shortcut: 'E' },
      { id: 'learning-loop', labelKey: 'navigation:items.learningLoop', icon: Brain, shortcut: 'L' },
    ],
    defaultExpanded: false
  },
  {
    id: 'integration',
    labelKey: 'navigation:groups.integration',
    icon: GitFork,
    items: [
      { id: 'worktrees', labelKey: 'navigation:items.worktrees', icon: GitBranch, shortcut: 'W' },
      { id: 'mcp-marketplace', labelKey: 'navigation:items.mcpMarketplace', icon: Store, shortcut: 'X' },
    ],
    defaultExpanded: false
  },
  {
    id: 'planning',
    labelKey: 'navigation:groups.planning',
    icon: BarChart3,
    items: [
      { id: 'roadmap', labelKey: 'navigation:items.roadmap', icon: Map, shortcut: 'D' },
      { id: 'dashboard', labelKey: 'navigation:items.dashboard', icon: BarChart3, shortcut: 'H' },
      { id: 'analytics', labelKey: 'navigation:items.analytics', icon: Database, shortcut: 'A' },
      { id: 'cost-estimator', labelKey: 'navigation:items.costEstimator', icon: Coins, shortcut: 'E' },
      { id: 'session-history', labelKey: 'navigation:items.sessionHistory', icon: History, shortcut: 'S' },
    ],
    defaultExpanded: false
  },
  {
    id: 'knowledge',
    labelKey: 'navigation:groups.knowledge',
    icon: BookOpen,
    items: [
      { id: 'context', labelKey: 'navigation:items.context', icon: BookOpen, shortcut: 'C' },
      { id: 'ideation', labelKey: 'navigation:items.ideation', icon: Lightbulb, shortcut: 'I' },
      { id: 'changelog', labelKey: 'navigation:items.changelog', icon: FileText, shortcut: 'L' },
    ],
    defaultExpanded: false
  },
  {
    id: 'utilities',
    labelKey: 'navigation:groups.utilities',
    icon: Layers,
    items: [
      { id: 'voice-control', labelKey: 'navigation:items.voiceControl', icon: Mic, shortcut: 'V' },
      { id: 'migration', labelKey: 'navigation:items.migration', icon: Download, shortcut: 'Z' },
    ],
    defaultExpanded: false
  }
];

// GitHub nav items shown when GitHub is enabled
const githubNavItems: NavItem[] = [
  { id: 'github-issues', labelKey: 'navigation:items.githubIssues', icon: Github, shortcut: 'G' },
  { id: 'github-prs', labelKey: 'navigation:items.githubPRs', icon: GitPullRequest, shortcut: 'P' }
];

// GitLab nav items shown when GitLab is enabled
const gitlabNavItems: NavItem[] = [
  { id: 'gitlab-issues', labelKey: 'navigation:items.gitlabIssues', icon: GitlabIcon, shortcut: 'B' },
  { id: 'gitlab-merge-requests', labelKey: 'navigation:items.gitlabMRs', icon: GitMerge, shortcut: 'R' }
];

export function Sidebar({
  onSettingsClick,
  onNewTaskClick,
  activeView = 'kanban',
  onViewChange
}: SidebarProps) {
  const { t } = useTranslation(['navigation', 'dialogs', 'common']);
  const projects = useProjectStore((state) => state.projects);
  const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
  const settings = useSettingsStore((state) => state.settings);

  const [showAddProjectModal, setShowAddProjectModal] = useState(false);
  const [showGitSetupModal, setShowGitSetupModal] = useState(false);
  const [gitStatus, setGitStatus] = useState<GitStatus | null>(null);
  const [pendingProject, setPendingProject] = useState<Project | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['core'])); // Core group expanded by default

  const [showGitHubSetup, setShowGitHubSetup] = useState(false);
  const [gitHubSetupProject, setGitHubSetupProject] = useState<Project | null>(null);
  const [showAzureDevOpsSetup, setShowAzureDevOpsSetup] = useState(false);
  const [azureDevOpsSetupProject, setAzureDevOpsSetupProject] = useState<Project | null>(null);

  // AI Tools states - managed by individual stores
  const [showVoiceControlDialog, setShowVoiceControlDialog] = useState(false);

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  // Sidebar collapsed state from settings
  const isCollapsed = settings.sidebarCollapsed ?? false;

  const toggleSidebar = () => {
    saveSettings({ sidebarCollapsed: !isCollapsed });
  };

  // Subscribe to project-env-store for reactive GitHub/GitLab tab visibility
  const githubEnabled = useProjectEnvStore((state) => state.envConfig?.githubEnabled ?? false);
  const gitlabEnabled = useProjectEnvStore((state) => state.envConfig?.gitlabEnabled ?? false);

  // Track the last loaded project ID to avoid redundant loads
  const lastLoadedProjectIdRef = useRef<string | null>(null);

  // Compute visible nav groups based on GitHub/GitLab enabled state from store
  const visibleNavGroups = useMemo(() => {
    const groups = [...navGroups];
    
    // Add GitHub/GitLab items to integration group if enabled
    const integrationGroup = groups.find(g => g.id === 'integration');
    if (integrationGroup) {
      const integrationItems = [...integrationGroup.items];
      if (githubEnabled) {
        integrationItems.push(...githubNavItems);
      }
      if (gitlabEnabled) {
        integrationItems.push(...gitlabNavItems);
      }
      integrationGroup.items = integrationItems;
    }
    
    return groups;
  }, [githubEnabled, gitlabEnabled]);

  // Get all visible items for keyboard shortcuts
  const visibleNavItems = useMemo(() => {
    return visibleNavGroups.flatMap(group => group.items);
  }, [visibleNavGroups]);

  // Load envConfig when project changes to ensure store is populated
  useEffect(() => {
    // Track whether this effect is still current (for race condition handling)
    let isCurrent = true;

    const initializeEnvConfig = async () => {
      if (selectedProject?.id && selectedProject?.autoBuildPath) {
        // Only reload if the project ID differs from what we last loaded
        if (selectedProject.id !== lastLoadedProjectIdRef.current) {
          lastLoadedProjectIdRef.current = selectedProject.id;
          await loadProjectEnvConfig(selectedProject.id);
          // Check if this effect was cancelled while loading
          if (!isCurrent) return;
        }
      } else {
        // Clear the store if no project is selected or has no autoBuildPath
        lastLoadedProjectIdRef.current = null;
        clearProjectEnvConfig();
      }
    };
    initializeEnvConfig();

    // Cleanup function to mark this effect as stale
    return () => {
      isCurrent = false;
    };
  }, [selectedProject?.id, selectedProject?.autoBuildPath]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement ||
        (e.target as HTMLElement)?.isContentEditable
      ) {
        return;
      }

      // Only handle shortcuts when a project is selected
      if (!selectedProjectId) return;

      // Check for modifier keys - we want plain key presses only
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key.toUpperCase();

      // Find matching nav item from visible items only
      const matchedItem = visibleNavItems.find((item) => item.shortcut === key);

      if (matchedItem) {
        e.preventDefault();
        onViewChange?.(matchedItem.id);
      }
    };

    globalThis.addEventListener('keydown', handleKeyDown);
    return () => globalThis.removeEventListener('keydown', handleKeyDown);
  }, [selectedProjectId, onViewChange, visibleNavItems]);

  // Check git status when a project changes
  useEffect(() => {
    const checkGit = async () => {
      if (selectedProject) {
        try {
          const result = await globalThis.electronAPI.checkGitStatus(selectedProject.path);
          if (result.success && result.data) {
            setGitStatus(result.data);
            // Show git setup modal if a project is not a git repo or has no commits
            if (!result.data.isGitRepo || !result.data.hasCommits) {
              setShowGitSetupModal(true);
            }
          }
        } catch (error) {
          console.error('Failed to check git status:', error);
        }
      } else {
        setGitStatus(null);
      }
    };
    checkGit();
  }, [selectedProject]);

  const inferProviderFromRemote = (provider: 'github' | 'azure_devops' | 'unknown', remoteUrl?: string) => {
    if (provider !== 'unknown' || !remoteUrl) return provider;
    if (/github\.com[:/]/i.test(remoteUrl)) return 'github';
    if (/dev\.azure\.com|visualstudio\.com|ssh\.dev\.azure\.com/i.test(remoteUrl)) return 'azure_devops';
    return 'unknown';
  };

  const handleProjectAdded = async (project: Project, needsInit: boolean) => {
    if (needsInit) {
      setPendingProject(project);
      return;
    }

    try {
      const envResult = await globalThis.electronAPI.getProjectEnv(project.id);
      const envConfig = envResult.success ? envResult.data : null;
      const hasProvider = !!(envConfig?.githubEnabled || envConfig?.azureDevOpsEnabled);
      if (!hasProvider) {
        const detectionResult = await globalThis.electronAPI.detectRepoProvider(project.path);
        const rawProvider = detectionResult.success ? (detectionResult.data?.provider ?? 'unknown') : 'unknown';
        const provider = inferProviderFromRemote(rawProvider, detectionResult.data?.remoteUrl);

        setShowGitHubSetup(false);
        setGitHubSetupProject(null);
        setShowAzureDevOpsSetup(false);
        setAzureDevOpsSetupProject(null);

        if (provider === 'github') {
          setGitHubSetupProject(project);
          setShowGitHubSetup(true);
          return;
        }

        if (provider === 'azure_devops') {
          setAzureDevOpsSetupProject(project);
          setShowAzureDevOpsSetup(true);
          return;
        }
      }
    } catch {
      setShowGitHubSetup(false);
      setGitHubSetupProject(null);
      setShowAzureDevOpsSetup(false);
      setAzureDevOpsSetupProject(null);
    }
  };

  const handleGitInitialized = async () => {
    // Refresh git status after initialization
    if (selectedProject) {
      try {
        const result = await globalThis.electronAPI.checkGitStatus(selectedProject.path);
        if (result.success && result.data) {
          setGitStatus(result.data);
        }
      } catch (error) {
        console.error('Failed to refresh git status:', error);
      }
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
      await globalThis.electronAPI.updateProjectEnv(gitHubSetupProject.id, {
        githubEnabled: true,
        githubToken: settings.githubToken,
        githubRepo: settings.githubRepo,
        githubAuthMethod: settings.githubAuthMethod,
        azureDevOpsEnabled: false
      });

      await globalThis.electronAPI.updateProjectSettings(gitHubSetupProject.id, {
        mainBranch: settings.mainBranch
      });
    } catch (error) {
      console.error('Failed to save GitHub settings:', error);
    }

    setShowGitHubSetup(false);
    setGitHubSetupProject(null);
  };

  const handleGitHubSetupSkip = () => {
    setShowGitHubSetup(false);
    setGitHubSetupProject(null);
  };

  const handleAzureDevOpsSetupComplete = async () => {
    setShowAzureDevOpsSetup(false);
    setAzureDevOpsSetupProject(null);
  };

  const handleAzureDevOpsSetupSkip = () => {
    setShowAzureDevOpsSetup(false);
    setAzureDevOpsSetupProject(null);
  };

  const handleNavClick = (view: SidebarView) => {
    // Handle AI Tools that open dialogs instead of changing view
    if (view === 'test-generation') {
      openTestGenerationDialog();
      return;
    }
    if (view === 'prompt-optimizer') {
      openPromptOptimizerDialog();
      return;
    }
    if (view === 'context-aware-snippets') {
      openContextAwareSnippetsDialog();
      return;
    }
    if (view === 'code-playground') {
      openCodePlaygroundDialog();
      return;
    }
    if (view === 'conflict-predictor') {
      openConflictPredictorDialog();
      return;
    }
    if (view === 'dependency-sentinel') {
      openDependencySentinelDialog();
      return;
    }
    if (view === 'natural-language-git') {
      useNaturalLanguageGitStore.getState().openDialog();
      return;
    }
    if (view === 'voice-control') {
      setShowVoiceControlDialog(true);
      return;
    }
    if (view === 'app-emulator') {
      openAppEmulatorDialog();
      return;
    }
    if (view === 'learning-loop') {
      openLearningLoopDialog();
      return;
    }

    // Handle regular view changes
    onViewChange?.(view);
  };

const toggleGroupExpansion = (groupId: string) => {
    setExpandedGroups((prevSet) => {
      const newSet = new Set(prevSet);
      if (newSet.has(groupId)) {
        newSet.delete(groupId);
      } else {
        newSet.add(groupId);
      }
      return newSet;
    });
  };

  const renderNavItem = (item: NavItem, isSubItem = false) => {
    const isActive = activeView === item.id;
    const Icon = item.icon;

    // Determine CSS classes based on collapsed state and sub-item status
    const getLayoutClasses = () => {
      if (isCollapsed) {
        return 'justify-center px-2 py-2';
      }
      if (isSubItem) {
        return 'gap-3 px-3 py-1.5 ml-6';
      }
      return 'gap-3 px-3 py-2';
    };

    const button = (
      <button
        key={item.id}
        onClick={() => handleNavClick(item.id)}
        disabled={!selectedProjectId}
        aria-keyshortcuts={item.shortcut}
        className={cn(
          'flex w-full items-center rounded-lg text-sm transition-all duration-200',
          'hover:bg-accent hover:text-accent-foreground',
          'disabled:pointer-events-none disabled:opacity-50',
          isActive && 'bg-accent text-accent-foreground',
          getLayoutClasses()
        )}
      >
        <Icon className="h-4 w-4 shrink-0" />
        {!isCollapsed && (
          <>
            <span className="flex-1 text-left">{t(item.labelKey)}</span>
            {item.shortcut && (
              <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded-md border border-border bg-secondary px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:flex">
                {item.shortcut}
              </kbd>
            )}
          </>
        )}
      </button>
    );

    // Wrap in tooltip when collapsed
    if (isCollapsed) {
      return (
        <Tooltip key={item.id}>
          <TooltipTrigger asChild>{button}</TooltipTrigger>
          <TooltipContent side="right">
            <span>{t(item.labelKey)}</span>
            {item.shortcut && (
              <kbd className="ml-2 rounded border border-border bg-secondary px-1 font-mono text-[10px]">
                {item.shortcut}
              </kbd>
            )}
          </TooltipContent>
        </Tooltip>
      );
    }

    return button;
  };

  const renderNavGroup = (group: NavGroup) => {
    const isExpanded = expandedGroups.has(group.id);
    const GroupIcon = group.icon;
    const hasActiveItem = group.items.some(item => activeView === item.id);

    if (isCollapsed) {
      // In collapsed mode, show group icon with tooltip containing all items
      return (
        <Tooltip key={group.id}>
          <TooltipTrigger asChild>
            <div className="flex flex-col items-center gap-1 py-2">
              <div className={cn(
                "flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-200 hover:scale-105",
                hasActiveItem ? "bg-accent text-accent-foreground shadow-sm" : "hover:bg-accent hover:text-accent-foreground"
              )}>
                <GroupIcon className="h-4 w-4" />
              </div>
            </div>
          </TooltipTrigger>
          <TooltipContent side="right" className="max-w-xs">
            <div className="space-y-2">
              <p className="font-medium text-sm">{t(group.labelKey)}</p>
              <div className="space-y-1">
                {group.items.map(item => (
                  <div key={item.id} className="flex items-center gap-2 text-xs p-1 rounded hover:bg-accent/50">
                    <item.icon className="h-3 w-3 shrink-0" />
                    <span className="truncate">{t(item.labelKey)}</span>
                    {item.shortcut && (
                      <kbd className="rounded border border-border bg-secondary px-1 font-mono text-[9px] ml-auto">
                        {item.shortcut}
                      </kbd>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </TooltipContent>
        </Tooltip>
      );
    }

    return (
      <div key={group.id} className="space-y-1">
        <button
          onClick={() => toggleGroupExpansion(group.id)}
          className={cn(
            'flex w-full items-center rounded-lg text-sm transition-all duration-200 hover:scale-[1.02]',
            'hover:bg-accent hover:text-accent-foreground hover:shadow-sm',
            hasActiveItem && 'bg-accent/50 text-accent-foreground shadow-sm',
            'gap-3 px-3 py-2.5'
          )}
        >
          <div className={cn(
            "flex items-center justify-center w-8 h-8 rounded-md transition-colors",
            hasActiveItem ? "bg-primary/10 text-primary" : "text-muted-foreground"
          )}>
            <GroupIcon className="h-4 w-4" />
          </div>
          <span className="flex-1 text-left font-medium">{t(group.labelKey)}</span>
          <div className="flex items-center gap-1">
            <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full">
              {group.items.length}
            </span>
            <ChevronRight className={cn(
              'h-4 w-4 shrink-0 transition-transform duration-300 text-muted-foreground',
              isExpanded && 'rotate-90'
            )} />
          </div>
        </button>
        
        {isExpanded && (
          <div className="space-y-1 animate-in slide-in-from-top-2 duration-300 ease-out">
            {group.items.map((item, index) => (
              <div 
                key={item.id} 
                className="animate-in slide-in-from-left-2 duration-200 ease-out"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                {renderNavItem(item, true)}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <TooltipProvider>
      <div className={cn(
        "flex h-full flex-col bg-sidebar border-r border-border transition-all duration-300",
        isCollapsed ? "w-16" : "w-64"
      )}>
        {/* Header with drag area - extra top padding for macOS traffic lights */}
        <div className={cn(
          "electron-drag flex h-14 items-center pt-6 transition-all duration-300",
          isCollapsed ? "justify-center px-2" : "px-4"
        )}>
          {isCollapsed ? (
            <div className="electron-no-drag flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground font-bold text-sm">
              W
            </div>
          ) : (
            <span className="electron-no-drag text-lg font-bold text-primary">WorkPilot AI</span>
          )}
        </div>

        {/* Toggle button */}
        <div className={cn(
          "flex py-2 transition-all duration-300",
          isCollapsed ? "justify-center px-2" : "justify-end px-3"
        )}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={toggleSidebar}
                aria-label={isCollapsed ? t('actions.expandSidebar') : t('actions.collapseSidebar')}
              >
                {isCollapsed ? (
                  <PanelLeft className="h-4 w-4" />
                ) : (
                  <PanelLeftClose className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {isCollapsed ? t('actions.expandSidebar') : t('actions.collapseSidebar')}
            </TooltipContent>
          </Tooltip>
        </div>

        <Separator />

        {/* Navigation */}
        <ScrollArea className="flex-1">
          <div className={cn("py-4 transition-all duration-300", isCollapsed ? "px-2" : "px-3")}>
            {/* Navigation Groups */}
            <div className="space-y-2">
              {visibleNavGroups.map(renderNavGroup)}
            </div>
          </div>
        </ScrollArea>

        <Separator />

        {/* Rate Limit Indicator - shows when Claude is rate limited */}
        <RateLimitIndicator />

        {/* Update Banner - shows when app update is available */}
        <UpdateBanner />

        {/* Bottom section with Settings, Help, and New Task */}
        <div className={cn("space-y-3 transition-all duration-300", isCollapsed ? "p-2" : "p-4")}>
          {/* Claude Code Status Badge (ProviderSelector déplacé dans le popover) */}
          {!isCollapsed && <ClaudeCodeStatusBadge onNavigateToTerminals={() => onViewChange?.('terminals')} />}

          {/* Copilot CLI Status Badge */}
          {!isCollapsed && <CopilotCliStatusBadge onNavigateToTerminals={() => onViewChange?.('terminals')} />}

          {/* Settings and Help row */}
          <div className={cn(
            "flex items-center",
            isCollapsed ? "flex-col gap-1" : "gap-2"
          )}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size={isCollapsed ? "icon" : "sm"}
                  className={isCollapsed ? "" : "flex-1 justify-start gap-2"}
                  onClick={onSettingsClick}
                >
                  <Settings className="h-4 w-4" />
                  {!isCollapsed && t('actions.settings')}
                </Button>
              </TooltipTrigger>
              <TooltipContent side={isCollapsed ? "right" : "top"}>{t('tooltips.settings')}</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => globalThis.open('https://github.com/tleub-ebp/Auto-Claude_EBP/issues', '_blank')}
                  aria-label={t('tooltips.help')}
                >
                  <HelpCircle className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side={isCollapsed ? "right" : "top"}>{t('tooltips.help')}</TooltipContent>
            </Tooltip>
          </div>

          {/* New Task button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                className="w-full"
                size={isCollapsed ? "icon" : "default"}
                onClick={onNewTaskClick}
                disabled={!selectedProjectId || !selectedProject?.autoBuildPath}
              >
                <Plus className={isCollapsed ? "h-4 w-4" : "mr-2 h-4 w-4"} />
                {!isCollapsed && t('actions.newTask')}
              </Button>
            </TooltipTrigger>
            {isCollapsed && (
              <TooltipContent side="right">{t('actions.newTask')}</TooltipContent>
            )}
          </Tooltip>
          {!isCollapsed && selectedProject && !selectedProject.autoBuildPath && (
            <p className="mt-2 text-xs text-muted-foreground text-center">
              {t('messages.initializeToCreateTasks')}
            </p>
          )}
        </div>
      </div>

      {/* Add Project Modal */}
      <AddProjectModal
        open={showAddProjectModal}
        onOpenChange={setShowAddProjectModal}
        onProjectAdded={handleProjectAdded}
      />

      {/* Azure DevOps Setup Modal - configure Azure DevOps */}
      {azureDevOpsSetupProject && (
        <AzureDevOpsSetupModal
          open={showAzureDevOpsSetup}
          onOpenChange={setShowAzureDevOpsSetup}
          project={azureDevOpsSetupProject}
          onComplete={handleAzureDevOpsSetupComplete}
          onSkip={handleAzureDevOpsSetupSkip}
        />
      )}

      {/* GitHub Setup Modal - configure GitHub */}
      {gitHubSetupProject && !showAzureDevOpsSetup && (
        <GitHubSetupModal
          open={showGitHubSetup}
          onOpenChange={setShowGitHubSetup}
          project={gitHubSetupProject}
          onComplete={handleGitHubSetupComplete}
          onSkip={handleGitHubSetupSkip}
        />
      )}

      {/* Git Setup Modal */}
      <GitSetupModal
        open={showGitSetupModal}
        onOpenChange={setShowGitSetupModal}
        project={selectedProject || null}
        gitStatus={gitStatus}
        onGitInitialized={handleGitInitialized}
      />

      {/* AI Tools Dialogs */}
      <TestGenerationDialog />
      <PromptOptimizerDialog />
      <ContextAwareSnippetsDialog />
      <CodePlaygroundDialog />
      <ConflictPredictorDialog />
      <DependencySentinelDialog />
      <NaturalLanguageGitDialog />
      <VoiceControlDialog />
      <AppEmulatorDialog />
      <LearningLoopDialog />
    </TooltipProvider>
  );
}
