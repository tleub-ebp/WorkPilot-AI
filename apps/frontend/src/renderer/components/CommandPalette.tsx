import {
	BarChart3,
	BookOpen,
	BookOpenCheck,
	CalendarClock,
	Coins,
	Download,
	FileCode2,
	FileText,
	GitBranch,
	GitMerge,
	GitPullRequest,
	Globe,
	History,
	Keyboard,
	LayoutGrid,
	Lightbulb,
	type LucideIcon,
	// biome-ignore lint/suspicious/noShadowRestrictedNames: shadow name is intentional
	Map,
	PlusCircle,
	Router,
	Search,
	Settings,
	Shield,
	ShieldAlert,
	Sparkles,
	Sun,
	Terminal,
	Wand2,
	Wrench,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "../lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CommandCategory =
	| "tasks"
	| "navigation"
	| "agents"
	| "settings"
	| "providers"
	| "terminal"
	| "help";

export interface PaletteCommand {
	id: string;
	label: string;
	description: string;
	category: CommandCategory;
	icon: LucideIcon;
	shortcut?: string;
	keywords?: string[];
	handler?: () => void;
}

interface CommandPaletteProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onNavigate: (view: string) => void;
	onNewTask: () => void;
	onOpenSettings: () => void;
	onOpenSettingsSection?: (section: string) => void;
	onToggleTheme?: () => void;
}

// ---------------------------------------------------------------------------
// Fuzzy matching
// ---------------------------------------------------------------------------

function fuzzyMatch(
	query: string,
	text: string,
): { match: boolean; score: number } {
	if (!query) return { match: true, score: 0 };

	const q = query.toLowerCase();
	const t = text.toLowerCase();

	// Exact substring match — highest score
	if (t.includes(q)) {
		const bonus = t.startsWith(q) ? 20 : 0;
		return { match: true, score: 100 + bonus - t.length };
	}

	// Character-by-character fuzzy match
	let qi = 0;
	let score = 0;
	let lastMatchIndex = -1;

	for (let ti = 0; ti < t.length && qi < q.length; ti++) {
		if (t[ti] === q[qi]) {
			// Consecutive match bonus
			if (lastMatchIndex === ti - 1) {
				score += 8;
			}
			// Word boundary bonus
			else if (
				ti === 0 ||
				t[ti - 1] === " " ||
				t[ti - 1] === "-" ||
				t[ti - 1] === "_"
			) {
				score += 6;
			} else {
				score += 4;
			}
			lastMatchIndex = ti;
			qi++;
		}
	}

	if (qi === q.length) {
		// Penalize long texts
		score -= Math.max(0, t.length - q.length);
		return { match: true, score };
	}

	return { match: false, score: 0 };
}

// ---------------------------------------------------------------------------
// Built-in commands
// ---------------------------------------------------------------------------

function getBuiltinCommands(
	onNavigate: (view: string) => void,
	onNewTask: () => void,
	onOpenSettings: () => void,
	onToggleTheme?: () => void,
	onOpenSettingsSection?: (section: string) => void,
): PaletteCommand[] {
	return [
		{
			id: "create_task",
			label: "Create Task",
			description: "Create a new task in the Kanban board",
			category: "tasks",
			icon: PlusCircle,
			shortcut: "Ctrl+N",
			keywords: ["new", "add", "task", "create"],
			handler: onNewTask,
		},
		{
			id: "search_tasks",
			label: "Search Tasks",
			description: "Search and filter tasks",
			category: "tasks",
			icon: Search,
			shortcut: "/",
			keywords: ["find", "filter", "search"],
			handler: () => onNavigate("kanban"),
		},
		{
			id: "go_kanban",
			label: "Go to Kanban",
			description: "Navigate to the Kanban board",
			category: "navigation",
			icon: LayoutGrid,
			shortcut: "Ctrl+1",
			keywords: ["board", "tasks", "kanban"],
			handler: () => onNavigate("kanban"),
		},
		{
			id: "go_terminals",
			label: "Go to Terminals",
			description: "Navigate to the terminal view",
			category: "navigation",
			icon: Terminal,
			shortcut: "Ctrl+2",
			keywords: ["terminal", "shell", "console"],
			handler: () => onNavigate("terminals"),
		},
		{
			id: "go_insights",
			label: "Go to Insights",
			description: "Navigate to the AI Insights chat",
			category: "navigation",
			icon: Sparkles,
			shortcut: "Ctrl+3",
			keywords: ["insights", "ai", "chat", "analytics"],
			handler: () => onNavigate("insights"),
		},
		{
			id: "go_roadmap",
			label: "Go to Roadmap",
			description: "Navigate to the project roadmap",
			category: "navigation",
			icon: Map,
			shortcut: "Ctrl+4",
			keywords: ["roadmap", "plan", "timeline"],
			handler: () => onNavigate("roadmap"),
		},
		{
			id: "go_ideation",
			label: "Go to Ideation",
			description: "Navigate to the ideation view",
			category: "navigation",
			icon: Lightbulb,
			keywords: ["ideation", "brainstorm", "ideas"],
			handler: () => onNavigate("ideation"),
		},
		{
			id: "go_context",
			label: "Go to Context",
			description: "Navigate to the context view",
			category: "navigation",
			icon: BookOpen,
			keywords: ["context", "memory", "knowledge"],
			handler: () => onNavigate("context"),
		},
		{
			id: "go_agent_tools",
			label: "Go to Agent Tools",
			description: "Navigate to agent tools configuration",
			category: "navigation",
			icon: Wrench,
			keywords: ["tools", "agent", "mcp"],
			handler: () => onNavigate("agent-tools"),
		},
		{
			id: "go_changelog",
			label: "Go to Changelog",
			description: "Navigate to the changelog",
			category: "navigation",
			icon: FileText,
			keywords: ["changelog", "updates", "history"],
			handler: () => onNavigate("changelog"),
		},
		{
			id: "go_worktrees",
			label: "Go to Worktrees",
			description: "Navigate to Git worktrees",
			category: "navigation",
			icon: GitBranch,
			keywords: ["worktrees", "git", "branches"],
			handler: () => onNavigate("worktrees"),
		},
		{
			id: "go_dashboard",
			label: "Go to Dashboard",
			description: "View project metrics, KPIs, and analytics",
			category: "navigation",
			icon: BarChart3,
			keywords: ["dashboard", "metrics", "kpi", "analytics", "stats"],
			handler: () => onNavigate("dashboard"),
		},
		{
			id: "go_code_review",
			label: "Go to Code Review",
			description: "AI-powered code review with quality scoring",
			category: "navigation",
			icon: FileCode2,
			keywords: ["review", "code", "diff", "quality"],
			handler: () => onNavigate("code-review"),
		},
		{
			id: "go_refactoring",
			label: "Go to Refactoring",
			description: "Detect code smells and get refactoring proposals",
			category: "navigation",
			icon: Wand2,
			keywords: ["refactor", "smells", "clean", "code"],
			handler: () => onNavigate("refactoring"),
		},
		{
			id: "go_documentation",
			label: "Go to Documentation",
			description: "Check coverage and generate docstrings",
			category: "navigation",
			icon: BookOpenCheck,
			keywords: ["docs", "documentation", "docstring", "readme"],
			handler: () => onNavigate("documentation"),
		},
		{
			id: "go_cost_estimator",
			label: "Go to Cost Estimator",
			description: "View LLM usage costs and budgets",
			category: "navigation",
			icon: Coins,
			keywords: ["cost", "budget", "spending", "tokens", "money"],
			handler: () => onNavigate("cost-estimator"),
		},
		{
			id: "go_session_history",
			label: "Go to Session History",
			description: "Track agent session performance and costs",
			category: "navigation",
			icon: History,
			keywords: ["sessions", "history", "timeline", "past"],
			handler: () => onNavigate("session-history"),
		},
		{
			id: "go_migration",
			label: "Go to Migration",
			description: "Framework migration wizard",
			category: "navigation",
			icon: Download,
			keywords: ["migration", "framework", "upgrade", "wizard"],
			handler: () => onNavigate("migration"),
		},
		{
			id: "go_visual_programming",
			label: "Go to Visual Programming",
			description: "Visual node-based programming interface",
			category: "navigation",
			icon: Sparkles,
			keywords: ["visual", "programming", "nodes", "flow"],
			handler: () => onNavigate("visual-programming"),
		},
		{
			id: "go_github_issues",
			label: "Go to GitHub Issues",
			description: "View and manage GitHub issues",
			category: "navigation",
			icon: Globe,
			keywords: ["github", "issues", "bugs", "tickets"],
			handler: () => onNavigate("github-issues"),
		},
		{
			id: "go_github_prs",
			label: "Go to GitHub PRs",
			description: "View and review GitHub pull requests",
			category: "navigation",
			icon: GitPullRequest,
			keywords: ["github", "pull", "requests", "prs", "review"],
			handler: () => onNavigate("github-prs"),
		},
		{
			id: "go_gitlab_issues",
			label: "Go to GitLab Issues",
			description: "View and manage GitLab issues",
			category: "navigation",
			icon: GitMerge,
			keywords: ["gitlab", "issues", "bugs", "tickets"],
			handler: () => onNavigate("gitlab-issues"),
		},
		{
			id: "go_gitlab_merge_requests",
			label: "Go to GitLab Merge Requests",
			description: "View and review GitLab merge requests",
			category: "navigation",
			icon: GitMerge,
			keywords: ["gitlab", "merge", "requests", "mrs", "review"],
			handler: () => onNavigate("gitlab-merge-requests"),
		},
		{
			id: "go_settings",
			label: "Open Settings",
			description: "Open application settings",
			category: "settings",
			icon: Settings,
			shortcut: "Ctrl+,",
			keywords: ["settings", "preferences", "config"],
			handler: onOpenSettings,
		},
		...(onOpenSettingsSection
			? [
					{
						id: "open_sandbox_settings",
						label: "Open Sandbox Settings",
						description:
							"Agent execution isolation, file whitelist, resource limits",
						category: "settings" as CommandCategory,
						icon: Shield,
						keywords: [
							"sandbox",
							"security",
							"isolation",
							"whitelist",
							"rollback",
						],
						handler: () => onOpenSettingsSection("sandbox"),
					},
					{
						id: "open_anomaly_settings",
						label: "Open Anomaly Detection Settings",
						description: "Agent behavior monitoring, trust scores, alerts",
						category: "settings" as CommandCategory,
						icon: ShieldAlert,
						keywords: [
							"anomaly",
							"detection",
							"trust",
							"score",
							"monitoring",
							"security",
						],
						handler: () => onOpenSettingsSection("anomaly-detection"),
					},
					{
						id: "open_router_settings",
						label: "Open LLM Router Settings",
						description:
							"Provider routing strategy, fallback chains, A/B testing",
						category: "settings" as CommandCategory,
						icon: Router,
						keywords: [
							"router",
							"llm",
							"provider",
							"fallback",
							"ab",
							"testing",
							"routing",
						],
						handler: () => onOpenSettingsSection("llm-router"),
					},
					{
						id: "open_scheduler_settings",
						label: "Open Scheduler Settings",
						description: "Cron-like task scheduling, chains, priority queues",
						category: "settings" as CommandCategory,
						icon: CalendarClock,
						keywords: [
							"scheduler",
							"cron",
							"schedule",
							"recurring",
							"chain",
							"queue",
						],
						handler: () => onOpenSettingsSection("scheduler"),
					},
				]
			: []),
		{
			id: "toggle_theme",
			label: "Toggle Theme",
			description: "Switch between light and dark theme",
			category: "settings",
			icon: Sun,
			keywords: ["theme", "dark", "light", "mode"],
			handler: onToggleTheme,
		},
		{
			id: "new_terminal",
			label: "New Terminal",
			description: "Open a new terminal tab",
			category: "terminal",
			icon: Terminal,
			shortcut: "Ctrl+Shift+T",
			keywords: ["terminal", "new", "shell"],
			handler: () => onNavigate("terminals"),
		},
		{
			id: "keyboard_shortcuts",
			label: "Keyboard Shortcuts",
			description: "Show all keyboard shortcuts",
			category: "help",
			icon: Keyboard,
			shortcut: "Ctrl+/",
			keywords: ["shortcuts", "keyboard", "keys", "help"],
		},
		{
			id: "export_report",
			label: "Export Report",
			description: "Export project report as JSON or CSV",
			category: "tasks",
			icon: Download,
			keywords: ["export", "report", "download", "csv", "json"],
		},
	];
}

// ---------------------------------------------------------------------------
// Category labels & colors
// ---------------------------------------------------------------------------

const CATEGORY_LABELS: Record<CommandCategory, string> = {
	tasks: "Tasks",
	navigation: "Navigation",
	agents: "Agents",
	settings: "Settings",
	providers: "Providers",
	terminal: "Terminal",
	help: "Help",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CommandPalette({
	open,
	onOpenChange,
	onNavigate,
	onNewTask,
	onOpenSettings,
	onOpenSettingsSection,
	onToggleTheme,
}: CommandPaletteProps) {
	// biome-ignore lint/correctness/noUnusedVariables: variable kept for clarity
	const { t } = useTranslation();
	const [query, setQuery] = useState("");
	const [selectedIndex, setSelectedIndex] = useState(0);
	const inputRef = useRef<HTMLInputElement>(null);
	const listRef = useRef<HTMLDivElement>(null);

	const commands = useMemo(
		() =>
			getBuiltinCommands(
				onNavigate,
				onNewTask,
				onOpenSettings,
				onToggleTheme,
				onOpenSettingsSection,
			),
		[
			onNavigate,
			onNewTask,
			onOpenSettings,
			onToggleTheme,
			onOpenSettingsSection,
		],
	);

	// Filtered & scored results
	const results = useMemo(() => {
		if (!query.trim()) {
			// Show navigation commands first when no query
			return commands.sort((a, b) => {
				const order: CommandCategory[] = [
					"navigation",
					"tasks",
					"agents",
					"terminal",
					"settings",
					"providers",
					"help",
				];
				return order.indexOf(a.category) - order.indexOf(b.category);
			});
		}

		const searchText = query.trim();
		const scored = commands
			.map((cmd) => {
				const labelMatch = fuzzyMatch(searchText, cmd.label);
				const descMatch = fuzzyMatch(searchText, cmd.description);
				const keywordScore = (cmd.keywords || []).reduce((best, kw) => {
					const m = fuzzyMatch(searchText, kw);
					return m.match && m.score > best ? m.score : best;
				}, 0);
				const bestScore = Math.max(
					labelMatch.match ? labelMatch.score : -Infinity,
					descMatch.match ? descMatch.score * 0.7 : -Infinity,
					keywordScore * 0.8,
				);
				return {
					cmd,
					score: bestScore,
					match: labelMatch.match || descMatch.match || keywordScore > 0,
				};
			})
			.filter((r) => r.match)
			.sort((a, b) => b.score - a.score);

		return scored.map((r) => r.cmd);
	}, [query, commands]);

	// Reset on open
	useEffect(() => {
		if (open) {
			setQuery("");
			setSelectedIndex(0);
			// Focus input after a small delay for the DOM to render
			requestAnimationFrame(() => inputRef.current?.focus());
		}
	}, [open]);

	// Reset selection when results change
	useEffect(() => {
		setSelectedIndex(0);
	}, []);

	// Scroll selected item into view
	useEffect(() => {
		if (!listRef.current) return;
		const items = listRef.current.querySelectorAll("[data-command-item]");
		items[selectedIndex]?.scrollIntoView({ block: "nearest" });
	}, [selectedIndex]);

	const executeCommand = useCallback(
		(cmd: PaletteCommand) => {
			onOpenChange(false);
			if (cmd.handler) {
				// Delay slightly so the palette closes first
				requestAnimationFrame(() => cmd.handler?.());
			}
		},
		[onOpenChange],
	);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			switch (e.key) {
				case "ArrowDown":
					e.preventDefault();
					setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
					break;
				case "ArrowUp":
					e.preventDefault();
					setSelectedIndex((i) => Math.max(i - 1, 0));
					break;
				case "Enter":
					e.preventDefault();
					if (results[selectedIndex]) {
						executeCommand(results[selectedIndex]);
					}
					break;
				case "Escape":
					e.preventDefault();
					onOpenChange(false);
					break;
			}
		},
		[results, selectedIndex, executeCommand, onOpenChange],
	);

	if (!open) return null;

	// Group results by category
	const grouped = results.reduce<Record<string, PaletteCommand[]>>(
		(acc, cmd) => {
			if (!acc[cmd.category]) acc[cmd.category] = [];
			acc[cmd.category].push(cmd);
			return acc;
		},
		{},
	);

	// Flatten for index tracking
	let flatIndex = 0;

	return (
		<div
			role="none"
			className="fixed inset-0 z-100"
			onClick={() => onOpenChange(false)}
			onKeyDown={(e) => e.key === "Escape" && onOpenChange(false)}
		>
			{/* Backdrop */}
			<div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

			{/* Palette */}
			<div
				className="absolute left-1/2 top-[20%] w-full max-w-lg -translate-x-1/2 animate-in fade-in slide-in-from-top-4 duration-200"
				onClick={(e) => e.stopPropagation()}
			>
				<div className="overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
					{/* Search input */}
					<div className="flex items-center gap-3 border-b border-border px-4 py-3">
						<Search className="h-4 w-4 shrink-0 text-muted-foreground" />
						<input
							ref={inputRef}
							value={query}
							onChange={(e) => setQuery(e.target.value)}
							onKeyDown={handleKeyDown}
							placeholder="Type a command or search..."
							className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
							spellCheck={false}
						/>
						<kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-border bg-secondary px-1.5 font-mono text-[10px] text-muted-foreground">
							ESC
						</kbd>
					</div>

					{/* Results list */}
					<div ref={listRef} className="max-h-80 overflow-y-auto p-2">
						{results.length === 0 ? (
							<div className="px-4 py-8 text-center text-sm text-muted-foreground">
								No commands found for "{query}"
							</div>
						) : (
							Object.entries(grouped).map(([category, cmds]) => (
								<div key={category}>
									<div className="px-2 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
										{CATEGORY_LABELS[category as CommandCategory] || category}
									</div>
									{cmds.map((cmd) => {
										const itemIndex = flatIndex++;
										const isSelected = itemIndex === selectedIndex;
										const Icon = cmd.icon;

										return (
											<button
												type="button"
												key={cmd.id}
												data-command-item
												onClick={() => executeCommand(cmd)}
												onMouseEnter={() => setSelectedIndex(itemIndex)}
												className={cn(
													"flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
													isSelected
														? "bg-accent text-accent-foreground"
														: "text-foreground hover:bg-accent/50",
												)}
											>
												<Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
												<div className="flex flex-1 flex-col items-start gap-0.5">
													<span className="font-medium">{cmd.label}</span>
													<span className="text-xs text-muted-foreground">
														{cmd.description}
													</span>
												</div>
												{cmd.shortcut && (
													<kbd className="ml-auto hidden sm:inline-flex h-5 items-center gap-1 rounded border border-border bg-secondary px-1.5 font-mono text-[10px] text-muted-foreground">
														{cmd.shortcut}
													</kbd>
												)}
											</button>
										);
									})}
								</div>
							))
						)}
					</div>

					{/* Footer */}
					<div className="flex items-center justify-between border-t border-border px-4 py-2 text-xs text-muted-foreground">
						<div className="flex items-center gap-3">
							<span className="flex items-center gap-1">
								<kbd className="rounded border border-border bg-secondary px-1 font-mono text-[10px]">
									↑↓
								</kbd>
								navigate
							</span>
							<span className="flex items-center gap-1">
								<kbd className="rounded border border-border bg-secondary px-1 font-mono text-[10px]">
									↵
								</kbd>
								select
							</span>
							<span className="flex items-center gap-1">
								<kbd className="rounded border border-border bg-secondary px-1 font-mono text-[10px]">
									esc
								</kbd>
								close
							</span>
						</div>
						<span>
							{results.length} command{results.length !== 1 ? "s" : ""}
						</span>
					</div>
				</div>
			</div>
		</div>
	);
}
