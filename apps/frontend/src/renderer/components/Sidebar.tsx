// React

// Types
import type { GitStatus, Project } from "@shared/types";
// Icons
import {
	Accessibility,
	AlertTriangle,
	BarChart3,
	BookOpen,
	BookOpenCheck,
	Box,
	Brain,
	Building2,
	Calendar,
	CheckCircle,
	ChevronRight,
	Code,
	Coins,
	Database,
	Download,
	FileCode2,
	FileEdit,
	FileJson,
	FileText,
	GitBranch,
	GitFork,
	GitMerge,
	GitPullRequest,
	Globe,
	HeartPulse,
	HelpCircle,
	History,
	Layers,
	LayoutGrid,
	Leaf,
	Lightbulb,
	// biome-ignore lint/suspicious/noShadowRestrictedNames: shadow name is intentional
	Map,
	Mic,
	Monitor,
	PanelLeft,
	PanelLeftClose,
	Plus,
	Puzzle,
	Rocket,
	RotateCcw,
	Search,
	Settings,
	Shield,
	ShieldAlert,
	ShieldCheck,
	Sparkles,
	Store,
	Swords,
	Target,
	Terminal,
	TestTube,
	UserCheck,
	Users,
	Wand2,
	WandSparkles,
	Wrench,
	X,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
// i18n
import { useTranslation } from "react-i18next";
import { ScrollArea } from "@/components/ui";
// Utils
import { cn } from "@/lib/utils";
import { openAppEmulatorDialog } from "@/stores/app-emulator-store";
import { openArenaDialog } from "@/stores/arena-store";
import { openCodePlaygroundDialog } from "@/stores/code-playground-store";
import { openConflictPredictorDialog } from "@/stores/conflict-predictor-store";
import { openContextAwareSnippetsDialog } from "@/stores/context-aware-snippets-store";
import { openDependencySentinelDialog } from "@/stores/dependency-sentinel-store";
import { openLearningLoopDialog } from "@/stores/learning-loop-store";
import { useNaturalLanguageGitStore } from "@/stores/natural-language-git-store";
import {
	clearProjectEnvConfig,
	loadProjectEnvConfig,
	useProjectEnvStore,
} from "@/stores/project-env-store";
// Stores
import { useProjectStore } from "@/stores/project-store";
import { openPromptOptimizerDialog } from "@/stores/prompt-optimizer-store";
import { saveSettings, useSettingsStore } from "@/stores/settings-store";
import { openTestGenerationDialog } from "@/stores/test-generation-store";
import { openVoiceControlDialog } from "@/stores/voice-control-store";
// Modals & Components
import { AddProjectModal } from "./AddProjectModal";
import { AzureDevOpsSetupModal } from "./AzureDevOpsSetupModal";
import { AppEmulatorDialog } from "./app-emulator/AppEmulatorDialog";
import { ArenaDialog } from "./arena/ArenaDialog";
import { ClaudeCodeStatusBadge } from "./ClaudeCodeStatusBadge";
import { CodexCliStatusBadge } from "./CodexCliStatusBadge";
import { CopilotCliStatusBadge } from "./CopilotCliStatusBadge";
import { CodePlaygroundDialog } from "./code-playground/CodePlaygroundDialog";
import { ConflictPredictorDialog } from "./conflict-predictor/ConflictPredictorDialog";
import { ContextAwareSnippetsDialog } from "./context-aware-snippets/ContextAwareSnippetsDialog";
import { DependencySentinelDialog } from "./dependency-sentinel/DependencySentinelDialog";
import { GitHubSetupModal } from "./GitHubSetupModal";
import { GitSetupModal } from "./GitSetupModal";
import { LearningLoopDialog } from "./learning-loop/LearningLoopDialog";
import { NaturalLanguageGitDialog } from "./natural-language-git/NaturalLanguageGitDialog";
import { PromptOptimizerDialog } from "./prompt-optimizer/PromptOptimizerDialog";
import { RateLimitIndicator } from "./RateLimitIndicator";
import { TestGenerationDialog } from "./test-generation/TestGenerationDialog";
import { UpdateBanner } from "./UpdateBanner";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui";
// UI
import { Button } from "./ui/button";
import { Separator } from "./ui/separator";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "./ui/tooltip";
import { VoiceControlDialog } from "./voice-control/VoiceControlDialog";

export type SidebarView =
	| "kanban"
	| "terminals"
	| "roadmap"
	| "context"
	| "ideation"
	| "github-issues"
	| "gitlab-issues"
	| "github-prs"
	| "gitlab-merge-requests"
	| "changelog"
	| "insights"
	| "worktrees"
	| "agent-tools"
	| "migration"
	| "visual-to-code"
	| "dashboard"
	| "analytics"
	| "code-review"
	| "refactoring"
	| "documentation"
	| "cost-estimator"
	| "session-history"
	| "voice-control"
	| "test-generation"
	| "prompt-optimizer"
	| "code-playground"
	| "dependency-sentinel"
	| "natural-language-git"
	| "conflict-predictor"
	| "context-aware-snippets"
	| "app-emulator"
	| "learning-loop"
	| "mcp-marketplace"
	| "mission-control"
	| "agent-replay"
	| "pixel-office"
	| "self-healing"
	| "browser-agent"
	| "pair-programming"
	| "pipeline-generator"
	| "plugin-marketplace"
	| "arena-mode"
	| "api-explorer"
	| "sandbox"
	| "regression-guardian"
	| "injection-guard"
	| "api-watcher"
	| "accessibility-agent"
	| "i18n-agent"
	| "onboarding-agent"
	| "flaky-tests"
	| "doc-drift"
	| "compliance"
	| "git-surgeon"
	| "release-coordinator"
	| "carbon-profiler"
	| "consensus-arbiter"
	| "notebook-agent"
	| "spec-refinement"
	| "agent-coach";

interface SidebarProps {
	readonly onSettingsClick: () => void;
	readonly onNewTaskClick: () => void;
	readonly activeView?: SidebarView;
	readonly onViewChange?: (view: SidebarView, force?: boolean) => void;
}

interface NavItem {
	id: SidebarView;
	labelKey: string;
	icon: React.ElementType;
	shortcut?: string;
	subGroup?: string; // i18n key for visual sub-group header within a group
}

interface NavGroup {
	id: string;
	labelKey: string;
	icon: React.ElementType;
	items: NavItem[];
	defaultExpanded?: boolean;
}

// Navigation groups organized by user intent
const navGroups: NavGroup[] = [
	{
		id: "workspace",
		labelKey: "navigation:groups.workspace",
		icon: Target,
		items: [
			{
				id: "kanban",
				labelKey: "navigation:items.kanban",
				icon: LayoutGrid,
				shortcut: "K",
			},
			{
				id: "mission-control",
				labelKey: "navigation:items.missionControl",
				icon: Rocket,
				shortcut: "Q",
			},
			{
				id: "dashboard",
				labelKey: "navigation:items.dashboard",
				icon: BarChart3,
				shortcut: "H",
			},
			{
				id: "session-history",
				labelKey: "navigation:items.sessionHistory",
				icon: History,
				shortcut: "S",
			},
		],
		defaultExpanded: true,
	},
	{
		id: "agents",
		labelKey: "navigation:groups.agents",
		icon: Rocket,
		items: [
			{
				id: "terminals",
				labelKey: "navigation:items.terminals",
				icon: Terminal,
				shortcut: "A",
			},
			{
				id: "pixel-office",
				labelKey: "navigation:items.pixelOffice",
				icon: Building2,
				shortcut: "P",
			},
			{
				id: "agent-replay",
				labelKey: "navigation:items.agentReplay",
				icon: RotateCcw,
				shortcut: "R",
			},
			{
				id: "self-healing",
				labelKey: "navigation:items.selfHealing",
				icon: HeartPulse,
				shortcut: "H",
			},
			{
				id: "arena-mode",
				labelKey: "navigation:items.arenaMode",
				icon: Swords,
				shortcut: "W",
			},
			{
				id: "consensus-arbiter",
				labelKey: "navigation:items.consensusArbiter",
				icon: Users,
				shortcut: "C",
			},
			{
				id: "agent-coach",
				labelKey: "navigation:items.agentCoach",
				icon: UserCheck,
				shortcut: "O",
			},
		],
		defaultExpanded: false,
	},
	{
		id: "development",
		labelKey: "navigation:groups.development",
		icon: Code,
		items: [
			{
				id: "pair-programming",
				labelKey: "navigation:items.pairProgramming",
				icon: Users,
				shortcut: "U",
			},
			{
				id: "code-review",
				labelKey: "navigation:items.codeReview",
				icon: FileCode2,
				shortcut: "V",
			},
			{
				id: "refactoring",
				labelKey: "navigation:items.refactoring",
				icon: Wand2,
				shortcut: "F",
			},
			{
				id: "test-generation",
				labelKey: "navigation:items.testGeneration",
				icon: TestTube,
				shortcut: "T",
			},
			{
				id: "code-playground",
				labelKey: "navigation:items.codePlayground",
				icon: Zap,
				shortcut: "G",
			},
			{
				id: "visual-to-code",
				labelKey: "navigation:items.visualToCode",
				icon: WandSparkles,
				shortcut: "Y",
			},
			{
				id: "documentation",
				labelKey: "navigation:items.documentation",
				icon: BookOpenCheck,
				shortcut: "O",
			},
			{
				id: "flaky-tests",
				labelKey: "navigation:items.flakyTests",
				icon: AlertTriangle,
				shortcut: "F",
			},
		],
		defaultExpanded: false,
	},
	{
		id: "explore",
		labelKey: "navigation:groups.explore",
		icon: Sparkles,
		items: [
			{
				id: "insights",
				labelKey: "navigation:items.insights",
				icon: Sparkles,
				shortcut: "N",
			},
			{
				id: "context",
				labelKey: "navigation:items.context",
				icon: BookOpen,
				shortcut: "C",
			},
			{
				id: "ideation",
				labelKey: "navigation:items.ideation",
				icon: Lightbulb,
				shortcut: "I",
			},
			{
				id: "learning-loop",
				labelKey: "navigation:items.learningLoop",
				icon: Brain,
				shortcut: "L",
			},
		],
		defaultExpanded: false,
	},
	{
		id: "git-integrations",
		labelKey: "navigation:groups.gitIntegrations",
		icon: GitFork,
		items: [
			{
				id: "worktrees",
				labelKey: "navigation:items.worktrees",
				icon: GitBranch,
				shortcut: "W",
			},
			{
				id: "natural-language-git",
				labelKey: "navigation:items.naturalLanguageGit",
				icon: GitBranch,
				shortcut: "G",
			},
			{
				id: "conflict-predictor",
				labelKey: "navigation:items.conflictPredictor",
				icon: GitMerge,
				shortcut: "C",
			},
			{
				id: "git-surgeon",
				labelKey: "navigation:items.gitSurgeon",
				icon: GitBranch,
				shortcut: "S",
			},
		],
		defaultExpanded: false,
	},
	{
		id: "planning",
		labelKey: "navigation:groups.planning",
		icon: BarChart3,
		items: [
			{
				id: "roadmap",
				labelKey: "navigation:items.roadmap",
				icon: Map,
				shortcut: "D",
			},
			{
				id: "analytics",
				labelKey: "navigation:items.analytics",
				icon: Database,
				shortcut: "A",
			},
			{
				id: "cost-estimator",
				labelKey: "navigation:items.costEstimator",
				icon: Coins,
				shortcut: "E",
			},
			{
				id: "changelog",
				labelKey: "navigation:items.changelog",
				icon: FileText,
				shortcut: "L",
			},
			{
				id: "release-coordinator",
				labelKey: "navigation:items.releaseCoordinator",
				icon: Calendar,
				shortcut: "R",
			},
			{
				id: "carbon-profiler",
				labelKey: "navigation:items.carbonProfiler",
				icon: Leaf,
				shortcut: "C",
			},
		],
		defaultExpanded: false,
	},
	{
		id: "toolbox",
		labelKey: "navigation:groups.toolbox",
		icon: Wrench,
		items: [
			// Extensions
			{
				id: "agent-tools",
				labelKey: "navigation:items.agentTools",
				icon: Wrench,
				shortcut: "M",
				subGroup: "navigation:subGroups.extensions",
			},
			{
				id: "mcp-marketplace",
				labelKey: "navigation:items.mcpMarketplace",
				icon: Store,
				shortcut: "X",
				subGroup: "navigation:subGroups.extensions",
			},
			{
				id: "plugin-marketplace",
				labelKey: "navigation:items.pluginMarketplace",
				icon: Puzzle,
				shortcut: "J",
				subGroup: "navigation:subGroups.extensions",
			},
			// Code Quality & Testing
			{
				id: "regression-guardian",
				labelKey: "navigation:items.regressionGuardian",
				icon: ShieldAlert,
				shortcut: "R",
				subGroup: "navigation:subGroups.codeQuality",
			},
			{
				id: "injection-guard",
				labelKey: "navigation:items.injectionGuard",
				icon: ShieldCheck,
				shortcut: "I",
				subGroup: "navigation:subGroups.codeQuality",
			},
			{
				id: "compliance",
				labelKey: "navigation:items.compliance",
				icon: CheckCircle,
				shortcut: "C",
				subGroup: "navigation:subGroups.codeQuality",
			},
			{
				id: "dependency-sentinel",
				labelKey: "navigation:items.dependencySentinel",
				icon: Shield,
				shortcut: "D",
				subGroup: "navigation:subGroups.codeQuality",
			},
			// Documentation & Spec
			{
				id: "onboarding-agent",
				labelKey: "navigation:items.onboardingAgent",
				icon: BookOpen,
				shortcut: "O",
				subGroup: "navigation:subGroups.documentation",
			},
			{
				id: "doc-drift",
				labelKey: "navigation:items.docDrift",
				icon: FileText,
				shortcut: "D",
				subGroup: "navigation:subGroups.documentation",
			},
			{
				id: "spec-refinement",
				labelKey: "navigation:items.specRefinement",
				icon: FileEdit,
				shortcut: "S",
				subGroup: "navigation:subGroups.documentation",
			},
			// Accessibility & i18n
			{
				id: "accessibility-agent",
				labelKey: "navigation:items.accessibilityAgent",
				icon: Accessibility,
				shortcut: "A",
				subGroup: "navigation:subGroups.accessibility",
			},
			{
				id: "i18n-agent",
				labelKey: "navigation:items.i18nAgent",
				icon: Globe,
				shortcut: "I",
				subGroup: "navigation:subGroups.accessibility",
			},
			// API & Data
			{
				id: "api-explorer",
				labelKey: "navigation:items.apiExplorer",
				icon: Globe,
				shortcut: "X",
				subGroup: "navigation:subGroups.api",
			},
			{
				id: "api-watcher",
				labelKey: "navigation:items.apiWatcher",
				icon: FileJson,
				shortcut: "A",
				subGroup: "navigation:subGroups.api",
			},
			{
				id: "sandbox",
				labelKey: "navigation:items.sandbox",
				icon: Box,
				shortcut: "B",
				subGroup: "navigation:subGroups.api",
			},
			{
				id: "notebook-agent",
				labelKey: "navigation:items.notebookAgent",
				icon: FileCode2,
				shortcut: "N",
				subGroup: "navigation:subGroups.api",
			},
			// Automation
			{
				id: "app-emulator",
				labelKey: "navigation:items.appEmulator",
				icon: Monitor,
				shortcut: "E",
				subGroup: "navigation:subGroups.automation",
			},
			{
				id: "browser-agent",
				labelKey: "navigation:items.browserAgent",
				icon: Globe,
				shortcut: "B",
				subGroup: "navigation:subGroups.automation",
			},
			{
				id: "pipeline-generator",
				labelKey: "navigation:items.pipelineGenerator",
				icon: Layers,
				shortcut: "I",
				subGroup: "navigation:subGroups.automation",
			},
			// Utilities
			{
				id: "voice-control",
				labelKey: "navigation:items.voiceControl",
				icon: Mic,
				shortcut: "V",
				subGroup: "navigation:subGroups.utilities",
			},
			{
				id: "migration",
				labelKey: "navigation:items.migration",
				icon: Download,
				shortcut: "Z",
				subGroup: "navigation:subGroups.utilities",
			},
			{
				id: "prompt-optimizer",
				labelKey: "navigation:items.promptOptimizer",
				icon: WandSparkles,
				shortcut: "P",
				subGroup: "navigation:subGroups.utilities",
			},
			{
				id: "context-aware-snippets",
				labelKey: "navigation:items.contextAwareSnippets",
				icon: Code,
				shortcut: "S",
				subGroup: "navigation:subGroups.utilities",
			},
		],
		defaultExpanded: false,
	},
];

// GitHub nav items shown when GitHub is enabled
const githubNavItems: NavItem[] = [
	{
		id: "github-issues",
		labelKey: "navigation:items.githubIssues",
		icon: Globe,
		shortcut: "G",
	},
	{
		id: "github-prs",
		labelKey: "navigation:items.githubPRs",
		icon: GitPullRequest,
		shortcut: "P",
	},
];

// GitLab nav items shown when GitLab is enabled
const gitlabNavItems: NavItem[] = [
	{
		id: "gitlab-issues",
		labelKey: "navigation:items.gitlabIssues",
		icon: Globe,
		shortcut: "B",
	},
	{
		id: "gitlab-merge-requests",
		labelKey: "navigation:items.gitlabMRs",
		icon: GitMerge,
		shortcut: "R",
	},
];

export function Sidebar({
	onSettingsClick,
	onNewTaskClick,
	activeView = "kanban",
	onViewChange,
}: SidebarProps) {
	const { t } = useTranslation(["navigation", "dialogs", "common"]);
	const projects = useProjectStore((state) => state.projects);
	const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
	const settings = useSettingsStore((state) => state.settings);

	const [showAddProjectModal, setShowAddProjectModal] = useState(false);
	const [showGitSetupModal, setShowGitSetupModal] = useState(false);
	const gitSetupSkippedForProjectRef = useRef<string | null>(null);
	const [gitStatus, setGitStatus] = useState<GitStatus | null>(null);
	const [_pendingProject, setPendingProject] = useState<Project | null>(null);
	const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
		new Set(["workspace"]),
	); // Workspace group expanded by default
	const [searchQuery, setSearchQuery] = useState("");
	const [isSearchOpen, setIsSearchOpen] = useState(false);
	const searchInputRef = useRef<HTMLInputElement>(null);

	const [showGitHubSetup, setShowGitHubSetup] = useState(false);
	const [gitHubSetupProject, setGitHubSetupProject] = useState<Project | null>(
		null,
	);
	const [showAzureDevOpsSetup, setShowAzureDevOpsSetup] = useState(false);
	const [azureDevOpsSetupProject, setAzureDevOpsSetupProject] =
		useState<Project | null>(null);

	const selectedProject = projects.find((p) => p.id === selectedProjectId);

	// Sidebar collapsed state from settings
	const isCollapsed = settings.sidebarCollapsed ?? false;

	// Sidebar resizable width
	const SIDEBAR_MIN_WIDTH = 200;
	const SIDEBAR_MAX_WIDTH = 480;
	const SIDEBAR_DEFAULT_WIDTH = 256;
	const SIDEBAR_COLLAPSED_WIDTH = 64;

	const sidebarWidth = settings.sidebarWidth ?? SIDEBAR_DEFAULT_WIDTH;
	const [isResizing, setIsResizing] = useState(false);
	const [resizeWidth, setResizeWidth] = useState(sidebarWidth);
	const resizingRef = useRef(false);

	// Sync resizeWidth when settings change externally
	useEffect(() => {
		if (!resizingRef.current) {
			setResizeWidth(settings.sidebarWidth ?? SIDEBAR_DEFAULT_WIDTH);
		}
	}, [settings.sidebarWidth]);

	const handleResizeStart = useCallback(
		(e: React.MouseEvent) => {
			e.preventDefault();
			resizingRef.current = true;
			setIsResizing(true);
			const startX = e.clientX;
			const startWidth = resizeWidth;

			const handleMouseMove = (moveEvent: MouseEvent) => {
				const newWidth = Math.min(
					SIDEBAR_MAX_WIDTH,
					Math.max(
						SIDEBAR_MIN_WIDTH,
						startWidth + (moveEvent.clientX - startX),
					),
				);
				setResizeWidth(newWidth);
			};

			const handleMouseUp = () => {
				resizingRef.current = false;
				setIsResizing(false);
				document.removeEventListener("mousemove", handleMouseMove);
				document.removeEventListener("mouseup", handleMouseUp);
				// Persist final width
				setResizeWidth((prev) => {
					saveSettings({ sidebarWidth: prev });
					return prev;
				});
			};

			document.addEventListener("mousemove", handleMouseMove);
			document.addEventListener("mouseup", handleMouseUp);
		},
		[resizeWidth],
	);

	const toggleSidebar = () => {
		saveSettings({ sidebarCollapsed: !isCollapsed });
	};

	// CLI panel expanded state persisted in settings (default: true)
	const isCliPanelExpanded = settings.cliPanelExpanded ?? true;
	const setIsCliPanelExpanded = (value: boolean) =>
		saveSettings({ cliPanelExpanded: value });

	// Subscribe to project-env-store for reactive GitHub/GitLab tab visibility
	const githubEnabled = useProjectEnvStore(
		(state) => state.envConfig?.githubEnabled ?? false,
	);
	const gitlabEnabled = useProjectEnvStore(
		(state) => state.envConfig?.gitlabEnabled ?? false,
	);

	// Track the last loaded project ID to avoid redundant loads
	const lastLoadedProjectIdRef = useRef<string | null>(null);

	// Compute visible nav groups based on GitHub/GitLab enabled state from store
	const visibleNavGroups = useMemo(() => {
		const groups = [...navGroups];

		// Add GitHub/GitLab items to integration group if enabled
		const integrationGroup = groups.find((g) => g.id === "git-integrations");
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
		return visibleNavGroups.flatMap((group) => group.items);
	}, [visibleNavGroups]);

	// Filter nav groups based on search query
	const filteredNavGroups = useMemo(() => {
		if (!searchQuery.trim()) return visibleNavGroups;
		const query = searchQuery.toLowerCase().trim();
		return visibleNavGroups
			.map((group) => ({
				...group,
				items: group.items.filter((item) =>
					t(item.labelKey).toLowerCase().includes(query),
				),
			}))
			.filter((group) => group.items.length > 0);
	}, [visibleNavGroups, searchQuery, t]);

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

			// "/" opens and focuses the search input when sidebar is expanded
			if (e.key === "/" && !isCollapsed) {
				e.preventDefault();
				setIsSearchOpen(true);
				requestAnimationFrame(() => searchInputRef.current?.focus());
				return;
			}

			const key = e.key.toUpperCase();

			// Find matching nav item from visible items only
			const matchedItem = visibleNavItems.find((item) => item.shortcut === key);

			if (matchedItem) {
				e.preventDefault();
				onViewChange?.(matchedItem.id);
			}
		};

		globalThis.addEventListener("keydown", handleKeyDown);
		return () => globalThis.removeEventListener("keydown", handleKeyDown);
	}, [selectedProjectId, onViewChange, visibleNavItems, isCollapsed]);

	// Check git status when a project changes
	useEffect(() => {
		// Reset the skip flag when the project changes so the modal shows for new projects
		gitSetupSkippedForProjectRef.current = null;

		const checkGit = async () => {
			if (selectedProject) {
				try {
					const result = await globalThis.electronAPI.checkGitStatus(
						selectedProject.path,
					);
					if (result.success && result.data) {
						setGitStatus(result.data);
						// Show git setup modal if a project is not a git repo or has no commits,
						// but only if the user hasn't explicitly dismissed it for this project yet
						if (
							(!result.data.isGitRepo || !result.data.hasCommits) &&
							gitSetupSkippedForProjectRef.current !== selectedProject.id
						) {
							setShowGitSetupModal(true);
						}
					}
				} catch (error) {
					console.error("Failed to check git status:", error);
				}
			} else {
				setGitStatus(null);
			}
		};
		checkGit();
	}, [selectedProject]);

	const inferProviderFromRemote = (
		provider: "github" | "azure_devops" | "unknown",
		remoteUrl?: string,
	) => {
		if (provider !== "unknown" || !remoteUrl) return provider;
		if (/github\.com[:/]/i.test(remoteUrl)) return "github";
		if (
			/dev\.azure\.com|visualstudio\.com|ssh\.dev\.azure\.com/i.test(remoteUrl)
		)
			return "azure_devops";
		return "unknown";
	};

	const handleProjectAdded = async (project: Project, needsInit: boolean) => {
		if (needsInit) {
			setPendingProject(project);
			return;
		}

		try {
			const envResult = await globalThis.electronAPI.getProjectEnv(project.id);
			const envConfig = envResult.success ? envResult.data : null;
			const hasProvider = !!(
				envConfig?.githubEnabled || envConfig?.azureDevOpsEnabled
			);
			if (!hasProvider) {
				const detectionResult = await globalThis.electronAPI.detectRepoProvider(
					project.path,
				);
				const rawProvider = detectionResult.success
					? (detectionResult.data?.provider ?? "unknown")
					: "unknown";
				const provider = inferProviderFromRemote(
					rawProvider,
					detectionResult.data?.remoteUrl,
				);

				setShowGitHubSetup(false);
				setGitHubSetupProject(null);
				setShowAzureDevOpsSetup(false);
				setAzureDevOpsSetupProject(null);

				if (provider === "github") {
					setGitHubSetupProject(project);
					setShowGitHubSetup(true);
					return;
				}

				if (provider === "azure_devops") {
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
				const result = await globalThis.electronAPI.checkGitStatus(
					selectedProject.path,
				);
				if (result.success && result.data) {
					setGitStatus(result.data);
				}
			} catch (error) {
				console.error("Failed to refresh git status:", error);
			}
		}
	};

	const handleGitHubSetupComplete = async (settings: {
		githubToken: string;
		githubRepo: string;
		mainBranch: string;
		githubAuthMethod?: "oauth" | "pat";
	}) => {
		if (!gitHubSetupProject) return;

		try {
			await globalThis.electronAPI.updateProjectEnv(gitHubSetupProject.id, {
				githubEnabled: true,
				githubToken: settings.githubToken,
				githubRepo: settings.githubRepo,
				githubAuthMethod: settings.githubAuthMethod,
				azureDevOpsEnabled: false,
			});

			await globalThis.electronAPI.updateProjectSettings(
				gitHubSetupProject.id,
				{
					mainBranch: settings.mainBranch,
				},
			);
		} catch (error) {
			console.error("Failed to save GitHub settings:", error);
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
		// Clear search when navigating
		setSearchQuery("");
		setIsSearchOpen(false);

		// Handle AI Tools that open dialogs instead of changing view
		if (view === "test-generation") {
			openTestGenerationDialog();
			return;
		}
		if (view === "prompt-optimizer") {
			openPromptOptimizerDialog();
			return;
		}
		if (view === "context-aware-snippets") {
			openContextAwareSnippetsDialog();
			return;
		}
		if (view === "code-playground") {
			openCodePlaygroundDialog();
			return;
		}
		if (view === "conflict-predictor") {
			openConflictPredictorDialog();
			return;
		}
		if (view === "dependency-sentinel") {
			openDependencySentinelDialog();
			return;
		}
		if (view === "natural-language-git") {
			useNaturalLanguageGitStore.getState().openDialog();
			return;
		}
		if (view === "voice-control") {
			openVoiceControlDialog();
			return;
		}
		if (view === "app-emulator") {
			openAppEmulatorDialog();
			return;
		}
		if (view === "learning-loop") {
			openLearningLoopDialog();
			return;
		}
		if (view === "arena-mode") {
			openArenaDialog();
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
				return "justify-center px-2 py-2";
			}
			if (isSubItem) {
				return "gap-3 px-3 py-1.5 ml-6";
			}
			return "gap-3 px-3 py-2";
		};

		const button = (
			<button
				type="button"
				key={item.id}
				onClick={() => handleNavClick(item.id)}
				disabled={!selectedProjectId}
				aria-keyshortcuts={item.shortcut}
				className={cn(
					"flex w-[calc(100%-(--spacing(5)))] items-center rounded-lg text-sm transition-all duration-200",
					"hover:bg-accent hover:text-accent-foreground",
					"disabled:pointer-events-none disabled:opacity-50",
					isActive && "bg-accent text-accent-foreground",
					getLayoutClasses(),
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

	const groupItemsBySubGroup = (items: NavItem[]) => {
		const subGroups: { key: string; items: NavItem[] }[] = [];
		for (const item of items) {
			const key = item.subGroup ?? "";
			const last = subGroups.at(-1);
			if (last?.key === key) {
				last.items.push(item);
			} else {
				subGroups.push({ key, items: [item] });
			}
		}
		return subGroups;
	};

	const renderTooltipSubGroupItem = (item: NavItem) => (
		<div
			key={item.id}
			className="flex items-center gap-2 text-xs p-1 rounded hover:bg-accent/50"
		>
			<item.icon className="h-3 w-3 shrink-0" />
			<span className="truncate">{t(item.labelKey)}</span>
			{item.shortcut && (
				<kbd className="rounded border border-border bg-secondary px-1 font-mono text-[9px] ml-auto">
					{item.shortcut}
				</kbd>
			)}
		</div>
	);

	const renderTooltipItems = (items: NavItem[]) => {
		const hasSubGroups = items.some((item) => item.subGroup);

		if (!hasSubGroups) {
			return items.map(renderTooltipSubGroupItem);
		}

		const subGroups = groupItemsBySubGroup(items);
		return subGroups.map((sg, sgIndex) => (
			<div
				key={sg.key}
				className={cn(
					"rounded bg-white/4 border border-white/8 px-1 py-1",
					sgIndex > 0 && "mt-1",
				)}
			>
				{sg.key && (
					<div className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/60 px-1 pb-0.5">
						{t(sg.key)}
					</div>
				)}
				{sg.items.map(renderTooltipSubGroupItem)}
			</div>
		));
	};

	const renderExpandedSubGroupItem = (item: NavItem, delay: number) => (
		<div
			key={item.id}
			className="animate-in slide-in-from-left-2 duration-200 ease-out"
			style={{ animationDelay: `${delay}ms` }}
		>
			{renderNavItem(item, true)}
		</div>
	);

	const renderExpandedItems = (items: NavItem[]) => {
		const hasSubGroups = items.some((item) => item.subGroup);

		if (!hasSubGroups) {
			return (
				<div className="rounded-lg overflow-hidden bg-white/4 border border-white/8 px-1.5 py-1.5 space-y-0.5">
					{items.map((item, index) =>
						renderExpandedSubGroupItem(item, index * 50),
					)}
				</div>
			);
		}

		const subGroups = groupItemsBySubGroup(items);
		let itemIndex = 0;
		return subGroups.map((sg, sgIndex) => (
			<div
				key={sg.key}
				className={cn(
					"rounded-lg overflow-hidden bg-white/4 border border-white/8 px-1.5 py-1.5",
					sgIndex > 0 && "mt-2",
				)}
			>
				{sg.key && (
					<div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
						{t(sg.key)}
					</div>
				)}
				<div className="space-y-0.5">
					{sg.items.map((item) => {
						const delay = itemIndex * 50;
						itemIndex++;
						return renderExpandedSubGroupItem(item, delay);
					})}
				</div>
			</div>
		));
	};

	const renderNavGroup = (group: NavGroup) => {
		const isExpanded = searchQuery.trim() ? true : expandedGroups.has(group.id);
		const GroupIcon = group.icon;
		const hasActiveItem = group.items.some((item) => activeView === item.id);

		if (isCollapsed) {
			// In collapsed mode, show group icon with tooltip containing all items
			return (
				<Tooltip key={group.id}>
					<TooltipTrigger asChild>
						<div className="flex flex-col items-center gap-1 py-2">
							<div
								className={cn(
									"flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-200 hover:scale-105",
									hasActiveItem
										? "bg-accent text-accent-foreground shadow-sm"
										: "hover:bg-accent hover:text-accent-foreground",
								)}
							>
								<GroupIcon className="h-4 w-4" />
							</div>
						</div>
					</TooltipTrigger>
					<TooltipContent side="right" className="max-w-xs">
						<div className="space-y-2">
							<p className="font-medium text-sm">{t(group.labelKey)}</p>
							<div className="space-y-1">{renderTooltipItems(group.items)}</div>
						</div>
					</TooltipContent>
				</Tooltip>
			);
		}

		return (
			<div key={group.id} className="space-y-1">
				<button
					type="button"
					onClick={() => toggleGroupExpansion(group.id)}
					className={cn(
						"flex w-full items-center rounded-lg text-sm transition-all duration-200 hover:scale-[1.02]",
						"hover:bg-accent hover:text-accent-foreground hover:shadow-sm",
						hasActiveItem && "bg-accent/50 text-accent-foreground shadow-sm",
						"gap-3 px-3 py-2.5",
					)}
				>
					<div
						className={cn(
							"flex items-center justify-center w-8 h-8 rounded-md transition-colors",
							hasActiveItem
								? "bg-primary/10 text-primary"
								: "text-muted-foreground",
						)}
					>
						<GroupIcon className="h-4 w-4" />
					</div>
					<span className="flex-1 text-left font-medium">
						{t(group.labelKey)}
					</span>
					<div className="flex items-center gap-1">
						<span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full">
							{group.items.length}
						</span>
						<ChevronRight
							className={cn(
								"h-4 w-4 shrink-0 transition-transform duration-300 text-muted-foreground",
								isExpanded && "rotate-90",
							)}
						/>
					</div>
				</button>

				{isExpanded && (
					<div className="space-y-1 animate-in slide-in-from-top-2 duration-300 ease-out">
						{renderExpandedItems(group.items)}
					</div>
				)}
			</div>
		);
	};

	return (
		<TooltipProvider>
			<div
				className={cn(
					"relative flex h-full flex-col bg-sidebar border-r border-border",
					!isResizing && "transition-all duration-300",
				)}
				style={{ width: isCollapsed ? SIDEBAR_COLLAPSED_WIDTH : resizeWidth }}
			>
				{/* Header with drag area - extra top padding for macOS traffic lights */}
				<div
					className={cn(
						"electron-drag flex h-14 items-center pt-6 transition-all duration-300",
						isCollapsed ? "justify-center px-2" : "px-4",
					)}
				>
					{isCollapsed ? (
						<div className="electron-no-drag flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground font-bold text-sm">
							W
						</div>
					) : (
						<span className="electron-no-drag text-lg font-bold text-primary">
							WorkPilot AI
						</span>
					)}
				</div>

				{/* Toggle + Search row */}
				<div
					className={cn(
						"flex items-center py-2 transition-all duration-300",
						isCollapsed ? "justify-center px-2" : "justify-end gap-1 px-3",
					)}
				>
					{/* Search button / inline input â€” only when expanded */}
					{!isCollapsed && (
						<div
							className={cn(
								"flex items-center overflow-hidden rounded-md transition-all duration-300 ease-in-out",
								isSearchOpen
									? "flex-1 bg-muted/50 border border-border"
									: "flex-none",
							)}
						>
							{isSearchOpen ? (
								<div className="relative flex items-center w-full">
									<Search className="absolute left-2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
									<input
										ref={searchInputRef}
										type="text"
										value={searchQuery}
										onChange={(e) => setSearchQuery(e.target.value)}
										onKeyDown={(e) => {
											if (e.key === "Escape") {
												setSearchQuery("");
												setIsSearchOpen(false);
											}
										}}
										onBlur={() => {
											if (!searchQuery.trim()) {
												setIsSearchOpen(false);
											}
										}}
										placeholder={t("search.placeholder")}
										className="w-full bg-transparent pl-7 pr-7 py-1 text-sm placeholder:text-muted-foreground/60 focus:outline-none"
									/>
									{searchQuery && (
										<button
											type="button"
											onMouseDown={(e) => e.preventDefault()}
											onClick={() => {
												setSearchQuery("");
												searchInputRef.current?.focus();
											}}
											className="absolute right-1.5 text-muted-foreground hover:text-foreground transition-colors"
											aria-label={t("search.clear")}
										>
											<X className="h-3.5 w-3.5" />
										</button>
									)}
								</div>
							) : (
								<Tooltip>
									<TooltipTrigger asChild>
										<Button
											variant="ghost"
											size="icon"
											className="h-7 w-7 shrink-0"
											onClick={() => {
												setIsSearchOpen(true);
												requestAnimationFrame(() =>
													searchInputRef.current?.focus(),
												);
											}}
											aria-label={t("search.placeholder")}
										>
											<Search className="h-4 w-4" />
										</Button>
									</TooltipTrigger>
									<TooltipContent side="bottom">
										{t("search.placeholder")}
										<kbd className="ml-2 rounded border border-border bg-secondary px-1 font-mono text-[10px]">
											/
										</kbd>
									</TooltipContent>
								</Tooltip>
							)}
						</div>
					)}

					<Tooltip>
						<TooltipTrigger asChild>
							<Button
								variant="ghost"
								size="icon"
								className="h-7 w-7 shrink-0"
								onClick={toggleSidebar}
								aria-label={
									isCollapsed
										? t("actions.expandSidebar")
										: t("actions.collapseSidebar")
								}
							>
								{isCollapsed ? (
									<PanelLeft className="h-4 w-4" />
								) : (
									<PanelLeftClose className="h-4 w-4" />
								)}
							</Button>
						</TooltipTrigger>
						<TooltipContent side="right">
							{isCollapsed
								? t("actions.expandSidebar")
								: t("actions.collapseSidebar")}
						</TooltipContent>
					</Tooltip>
				</div>

				<Separator />

				{/* Navigation */}
				<ScrollArea className="flex-1">
					<div
						className={cn(
							"py-4 transition-all duration-300",
							isCollapsed ? "px-2" : "px-3",
						)}
					>
						{/* Navigation Groups */}
						<div className="space-y-2">
							{filteredNavGroups.map(renderNavGroup)}
							{!isCollapsed &&
								searchQuery.trim() &&
								filteredNavGroups.length === 0 && (
									<p className="px-3 py-4 text-sm text-center text-muted-foreground">
										{t("search.noResults")}
									</p>
								)}
						</div>
					</div>
				</ScrollArea>

				<Separator />

				{/* Rate Limit Indicator - shows when Claude is rate limited */}
				<RateLimitIndicator />

				{/* Update Banner - shows when app update is available */}
				<UpdateBanner />

				{/* Bottom section with CLI/Settings collapsible panel and New Task */}
				<div
					className={cn(
						"space-y-3 transition-all duration-300",
						isCollapsed ? "p-2" : "p-4",
					)}
				>
					{/* CLI/Settings Panel */}
					<Collapsible
						open={isCliPanelExpanded}
						onOpenChange={setIsCliPanelExpanded}
					>
						<CollapsibleTrigger asChild>
							<Button
								variant="ghost"
								size="sm"
								className={cn(
									"w-full justify-start gap-2 text-xs font-medium",
									isCollapsed ? "h-8 w-8 p-0" : "h-8",
								)}
							>
								<Wrench className="h-4 w-4" />
								{!isCollapsed && (
									<>
										<span>{t("common:actions.cliToolsAndSettings")}</span>
										<ChevronRight
											className={cn(
												"h-3 w-3 ml-auto transition-transform duration-200",
												isCliPanelExpanded && "rotate-90",
											)}
										/>
									</>
								)}
							</Button>
						</CollapsibleTrigger>

						<CollapsibleContent className="mt-2 space-y-2">
							{/* CLI Tools â€” compact grouped badges */}
							<div className="rounded-lg bg-white/4 border border-white/8 p-2 space-y-0.5">
								<ClaudeCodeStatusBadge
									onNavigateToTerminals={() => onViewChange?.("terminals", true)}
								/>
								<CopilotCliStatusBadge
									onNavigateToTerminals={() => onViewChange?.("terminals", true)}
								/>
								<CodexCliStatusBadge
									onNavigateToTerminals={() => onViewChange?.("terminals", true)}
								/>
							</div>

							{/* Settings and Help row */}
							<div
								className={cn(
									"flex items-center rounded-lg bg-white/4 border border-white/8 p-1.5",
									isCollapsed ? "flex-col gap-1" : "gap-2",
								)}
							>
								<Tooltip>
									<TooltipTrigger asChild>
										<Button
											variant="ghost"
											size={isCollapsed ? "icon" : "sm"}
											className={
												isCollapsed ? "" : "flex-1 justify-start gap-2"
											}
											onClick={onSettingsClick}
										>
											<Settings className="h-4 w-4" />
											{!isCollapsed && t("actions.settings")}
										</Button>
									</TooltipTrigger>
									<TooltipContent side={isCollapsed ? "right" : "top"}>
										{t("tooltips.settings")}
									</TooltipContent>
								</Tooltip>
								<Tooltip>
									<TooltipTrigger asChild>
										<Button
											variant="ghost"
											size="icon"
											onClick={() =>
												globalThis.open(
													"https://github.com/tleub-ebp/WorkPilot-AI/issues",
													"_blank",
												)
											}
											aria-label={t("tooltips.help")}
										>
											<HelpCircle className="h-4 w-4" />
										</Button>
									</TooltipTrigger>
									<TooltipContent side={isCollapsed ? "right" : "top"}>
										{t("tooltips.help")}
									</TooltipContent>
								</Tooltip>
							</div>
						</CollapsibleContent>
					</Collapsible>

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
								{!isCollapsed && t("actions.newTask")}
							</Button>
						</TooltipTrigger>
						{isCollapsed && (
							<TooltipContent side="right">
								{t("actions.newTask")}
							</TooltipContent>
						)}
					</Tooltip>
					{!isCollapsed &&
						selectedProject &&
						!selectedProject.autoBuildPath && (
							<p className="mt-2 text-xs text-muted-foreground text-center">
								{t("messages.initializeToCreateTasks")}
							</p>
						)}
				</div>

				{/* Resize handle */}
				{!isCollapsed && (
					// biome-ignore lint/a11y/noStaticElementInteractions: interactive handler is intentional
					// biome-ignore lint/a11y/noNoninteractiveElementInteractions: resize handle — mouse drag interaction
					<div
						onMouseDown={handleResizeStart}
						className={cn(
							"absolute top-0 right-0 w-1 h-full cursor-col-resize z-50 transition-colors",
							"hover:bg-primary/40",
							isResizing && "bg-primary/60",
						)}
					/>
				)}
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
				onOpenChange={(open) => {
					if (!open && selectedProject) {
						// Mark this project as skipped so the modal doesn't reopen due to async re-checks
						gitSetupSkippedForProjectRef.current = selectedProject.id;
					}
					setShowGitSetupModal(open);
				}}
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
			<VoiceControlDialog
				onExecuteCommand={(result) => {
					if (result.action === "navigate" && result.parameters?.destination) {
						onViewChange?.(result.parameters.destination as SidebarView);
					}
				}}
			/>
			<AppEmulatorDialog />
			<LearningLoopDialog />

			<ArenaDialog />
		</TooltipProvider>
	);
}
