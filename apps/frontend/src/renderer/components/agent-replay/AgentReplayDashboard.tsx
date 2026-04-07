import {
	Activity,
	AlertCircle,
	ArrowLeft,
	Brain,
	Bug,
	CheckCircle,
	ChevronRight,
	Code,
	DollarSign,
	Eye,
	FileText,
	Flame,
	GitCompare,
	Loader2,
	Maximize2,
	Minimize2,
	Pause,
	Play,
	Plus,
	RotateCcw,
	Search,
	SkipBack,
	SkipForward,
	Terminal,
	Trash2,
	Wrench,
	X,
	Zap,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
	type ABComparison,
	type ReplaySessionSummary,
	useAgentReplayStore,
} from "../../stores/agent-replay-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { ScrollArea } from "../ui/scroll-area";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatDuration = (ms: number) => {
	if (ms < 1000) return `${Math.round(ms)}ms`;
	if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
	return `${(ms / 60000).toFixed(1)}m`;
};

const formatTokens = (tokens: number) => {
	if (tokens < 1000) return tokens.toString();
	if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}K`;
	return `${(tokens / 1000000).toFixed(1)}M`;
};

const formatCost = (cost: number) => `$${cost.toFixed(4)}`;

const formatDate = (ts: number) => new Date(ts * 1000).toLocaleString();

const STEP_COLORS: Record<string, string> = {
	session_start: "bg-green-500",
	session_end: "bg-red-500",
	agent_thinking: "bg-blue-500",
	agent_response: "bg-purple-500",
	tool_call: "bg-orange-500",
	tool_result: "bg-yellow-500",
	file_read: "bg-cyan-500",
	file_create: "bg-emerald-500",
	file_update: "bg-indigo-500",
	file_delete: "bg-rose-500",
	command_run: "bg-amber-500",
	command_output: "bg-lime-500",
	test_run: "bg-teal-500",
	test_result: "bg-violet-500",
	decision: "bg-pink-500",
	error: "bg-red-600",
	progress: "bg-sky-500",
	breakpoint_hit: "bg-red-400",
};

const STEP_ICONS: Record<string, React.ReactNode> = {
	agent_thinking: <Brain className="h-3.5 w-3.5" />,
	agent_response: <Code className="h-3.5 w-3.5" />,
	tool_call: <Wrench className="h-3.5 w-3.5" />,
	tool_result: <CheckCircle className="h-3.5 w-3.5" />,
	command_run: <Terminal className="h-3.5 w-3.5" />,
	command_output: <Terminal className="h-3.5 w-3.5" />,
	error: <AlertCircle className="h-3.5 w-3.5" />,
	file_create: <Plus className="h-3.5 w-3.5" />,
	file_update: <FileText className="h-3.5 w-3.5" />,
	file_delete: <Trash2 className="h-3.5 w-3.5" />,
	decision: <GitCompare className="h-3.5 w-3.5" />,
	progress: <Activity className="h-3.5 w-3.5" />,
};

const getStepColor = (t: string) => STEP_COLORS[t] || "bg-gray-500";
const getStepIcon = (t: string) =>
	STEP_ICONS[t] || <Zap className="h-3.5 w-3.5" />;

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Session list view (no active session) */
const SessionListView: React.FC<{
	sessions: ReplaySessionSummary[];
	loading: boolean;
	onSelect: (id: string) => void;
	onDelete: (id: string) => void;
	onCompare: (a: string, b: string) => void;
}> = ({ sessions, loading, onSelect, onDelete, onCompare }) => {
	const { t } = useTranslation();
	const [compareA, setCompareA] = useState<string | null>(null);
	const [searchQuery, setSearchQuery] = useState("");

	const filtered = useMemo(() => {
		if (!searchQuery) return sessions;
		const q = searchQuery.toLowerCase();
		return sessions.filter(
			(s) =>
				s.agent_name.toLowerCase().includes(q) ||
				s.task_description.toLowerCase().includes(q) ||
				s.model_label.toLowerCase().includes(q),
		);
	}, [sessions, searchQuery]);

	if (loading) {
		return (
			<div className="flex items-center justify-center h-64">
				<Loader2 className="h-8 w-8 animate-spin" />
			</div>
		);
	}

	return (
		<div className="space-y-4 p-4 h-full overflow-auto">
			<div className="flex items-center justify-between">
				<h2 className="text-xl font-semibold flex items-center gap-2">
					<RotateCcw className="h-5 w-5" />
					{t("replay:title")}
				</h2>
				<div className="flex items-center gap-2">
					<div className="relative">
						<Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
						<Input
							placeholder={t("replay:searchSessions")}
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							className="pl-8 w-64"
						/>
					</div>
				</div>
			</div>

			{compareA && (
				<div className="p-3 rounded-lg border border-primary bg-primary/5 flex items-center justify-between">
					<span className="text-sm">
						Select a second session to compare with{" "}
						<strong>{compareA.slice(0, 8)}...</strong>
					</span>
					<Button variant="ghost" size="sm" onClick={() => setCompareA(null)}>
						<X className="h-4 w-4" />
					</Button>
				</div>
			)}

			{filtered.length === 0 ? (
				<Card>
					<CardContent className="py-12 text-center">
						<RotateCcw className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
						<p className="text-muted-foreground">
							{t("replay:noSessionsRecorded")}
						</p>
						<p className="text-sm text-muted-foreground mt-1">
							{t("replay:sessionsAutoRecorded")}
						</p>
					</CardContent>
				</Card>
			) : (
				<div className="space-y-2">
					{filtered.map((session) => (
						<Card
							key={session.session_id}
							className="cursor-pointer hover:border-primary/50 transition-colors"
							onClick={() => {
								if (compareA) {
									onCompare(compareA, session.session_id);
									setCompareA(null);
								} else {
									onSelect(session.session_id);
								}
							}}
						>
							<CardContent className="py-3 px-4">
								<div className="flex items-center justify-between">
									<div className="flex-1 min-w-0">
										<div className="flex items-center gap-2">
											<span className="font-medium truncate">
												{session.agent_name || "Agent"}
											</span>
											<Badge variant="secondary" className="text-xs">
												{session.agent_role}
											</Badge>
											<Badge
												variant={
													session.status === "completed"
														? "default"
														: "destructive"
												}
												className="text-xs"
											>
												{session.status}
											</Badge>
										</div>
										<p className="text-sm text-muted-foreground truncate mt-0.5">
											{session.task_description || "No description"}
										</p>
										<div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
											<span>{formatDate(session.start_time)}</span>
											<span>{session.step_count} steps</span>
											<span>{formatTokens(session.total_tokens)} tokens</span>
											<span>{formatCost(session.total_cost_usd)}</span>
											<span>{session.total_tool_calls} tools</span>
											<span>{session.total_file_changes} files</span>
											{session.model_label && (
												<Badge variant="outline" className="text-xs">
													{session.model_label}
												</Badge>
											)}
										</div>
									</div>
									<div className="flex items-center gap-1 ml-2">
										<Button
											variant="ghost"
											size="sm"
											onClick={(e) => {
												e.stopPropagation();
												setCompareA(session.session_id);
											}}
											title="A/B Compare"
										>
											<GitCompare className="h-4 w-4" />
										</Button>
										<Button
											variant="ghost"
											size="sm"
											onClick={(e) => {
												e.stopPropagation();
												onDelete(session.session_id);
											}}
											title="Delete"
										>
											<Trash2 className="h-4 w-4 text-destructive" />
										</Button>
										<ChevronRight className="h-4 w-4 text-muted-foreground" />
									</div>
								</div>
							</CardContent>
						</Card>
					))}
				</div>
			)}
		</div>
	);
};

/** File heatmap visualization */
const FileHeatmap: React.FC<{ heatmap: Record<string, number> }> = ({
	heatmap,
}) => {
	const { t } = useTranslation();
	const entries = useMemo(() => {
		const items = Object.entries(heatmap);
		const maxCount = Math.max(...items.map(([, c]) => c), 1);
		return items.map(([path, count]) => ({
			path,
			count,
			intensity: count / maxCount,
		}));
	}, [heatmap]);

	if (entries.length === 0) {
		return (
			<p className="text-sm text-muted-foreground">
				{t("replay:noFileChanges")}
			</p>
		);
	}

	return (
		<div className="space-y-1.5">
			{entries.map(({ path, count, intensity }) => {
				const shortPath = path.split("/").slice(-3).join("/");
				return (
					<div key={path} className="flex items-center gap-2">
						<div
							className="h-5 rounded-sm transition-all"
							style={{
								width: `${Math.max(intensity * 100, 8)}%`,
								backgroundColor: `hsl(${(1 - intensity) * 120}, 80%, 50%)`,
								opacity: 0.7 + intensity * 0.3,
							}}
						/>
						<span
							className="text-xs text-muted-foreground truncate flex-1"
							title={path}
						>
							{shortPath}
						</span>
						<Badge variant="outline" className="text-xs shrink-0">
							{count}
						</Badge>
					</div>
				);
			})}
		</div>
	);
};

/** Token timeline bar chart */
const TokenTimeline: React.FC<{
	timeline: Array<{
		step_index: number;
		input_tokens: number;
		output_tokens: number;
		cumulative: number;
	}>;
	currentIndex: number;
}> = ({ timeline, currentIndex }) => {
	const { t } = useTranslation();
	const maxTokens = useMemo(
		() => Math.max(...timeline.map((t) => t.input_tokens + t.output_tokens), 1),
		[timeline],
	);

	if (timeline.length === 0) {
		return (
			<p className="text-sm text-muted-foreground">{t("replay:noTokenData")}</p>
		);
	}

	return (
		<div className="flex items-end gap-px h-24">
			{timeline.map((entry) => {
				const total = entry.input_tokens + entry.output_tokens;
				const height = (total / maxTokens) * 100;
				const isCurrent = entry.step_index === currentIndex;
				return (
					<div
						key={entry.step_index}
						className="flex-1 min-w-[3px] relative group"
						title={`Step ${entry.step_index}: ${formatTokens(total)} tokens`}
					>
						<div
							className={`w-full rounded-t-sm transition-colors ${
								isCurrent ? "bg-primary" : "bg-primary/30 hover:bg-primary/50"
							}`}
							style={{ height: `${Math.max(height, 2)}%` }}
						/>
					</div>
				);
			})}
		</div>
	);
};

/** Metric row component for comparison panel */
const MetricRow: React.FC<{
	label: string;
	valA: string;
	valB: string;
	diff: string;
	positive?: boolean;
}> = ({ label, valA, valB, diff, positive }) => (
	<div className="grid grid-cols-4 gap-2 py-1.5 border-b border-border/50 text-sm">
		<span className="font-medium">{label}</span>
		<span className="text-center">{valA}</span>
		<span className="text-center">{valB}</span>
		<span
			className={`text-center font-medium ${positive ? "text-green-500" : "text-red-500"}`}
		>
			{diff}
		</span>
	</div>
);

/** A/B Comparison panel */
const ComparisonPanel: React.FC<{
	comparison: ABComparison;
	sessionA: ReplaySessionSummary | null;
	sessionB: ReplaySessionSummary | null;
	onClose: () => void;
}> = ({ comparison, sessionA, sessionB, onClose }) => {
	const { t } = useTranslation();

	return (
		<Card>
			<CardHeader>
				<div className="flex items-center justify-between">
					<CardTitle className="flex items-center gap-2">
						<GitCompare className="h-5 w-5" />
						{t("replay:abComparison")}
					</CardTitle>
					<Button variant="ghost" size="sm" onClick={onClose}>
						<X className="h-4 w-4" />
					</Button>
				</div>
			</CardHeader>
			<CardContent className="space-y-4">
				{/* Header row */}
				<div className="grid grid-cols-4 gap-2 text-xs font-medium text-muted-foreground border-b pb-2">
					<span>{t("replay:metric")}</span>
					<span className="text-center">{t("replay:sessionA")}</span>
					<span className="text-center">{t("replay:sessionB")}</span>
					<span className="text-center">{t("replay:diff")}</span>
				</div>

				<MetricRow
					label={t("replay:tokensLabel")}
					valA={formatTokens(sessionA?.total_tokens || 0)}
					valB={formatTokens(sessionB?.total_tokens || 0)}
					diff={`${comparison.token_diff > 0 ? "+" : ""}${formatTokens(comparison.token_diff)}`}
					positive={comparison.token_diff < 0}
				/>
				<MetricRow
					label={t("replay:cost")}
					valA={formatCost(sessionA?.total_cost_usd || 0)}
					valB={formatCost(sessionB?.total_cost_usd || 0)}
					diff={`${comparison.cost_diff > 0 ? "+" : ""}${formatCost(comparison.cost_diff)}`}
					positive={comparison.cost_diff < 0}
				/>
				<MetricRow
					label={t("replay:duration")}
					valA={formatDuration((sessionA?.duration_seconds || 0) * 1000)}
					valB={formatDuration((sessionB?.duration_seconds || 0) * 1000)}
					diff={`${comparison.duration_diff > 0 ? "+" : ""}${formatDuration(comparison.duration_diff * 1000)}`}
					positive={comparison.duration_diff < 0}
				/>
				<MetricRow
					label={t("replay:steps")}
					valA={String(sessionA?.step_count || 0)}
					valB={String(sessionB?.step_count || 0)}
					diff={`${comparison.step_count_diff > 0 ? "+" : ""}${comparison.step_count_diff}`}
					positive={comparison.step_count_diff < 0}
				/>
				<MetricRow
					label={t("replay:toolCalls")}
					valA={String(sessionA?.total_tool_calls || 0)}
					valB={String(sessionB?.total_tool_calls || 0)}
					diff={`${comparison.tool_calls_diff > 0 ? "+" : ""}${comparison.tool_calls_diff}`}
					positive={comparison.tool_calls_diff < 0}
				/>
				<MetricRow
					label={t("replay:fileChanges")}
					valA={String(sessionA?.total_file_changes || 0)}
					valB={String(sessionB?.total_file_changes || 0)}
					diff={`${comparison.file_changes_diff > 0 ? "+" : ""}${comparison.file_changes_diff}`}
					positive={comparison.file_changes_diff < 0}
				/>

				{/* Files comparison */}
				<div className="grid grid-cols-3 gap-3 mt-3">
					<div>
						<Label className="text-xs text-muted-foreground">
							{t("replay:commonFiles")}
						</Label>
						<div className="mt-1 space-y-0.5">
							{comparison.common_files.slice(0, 5).map((f) => (
								<Badge
									key={f}
									variant="secondary"
									className="text-xs block truncate"
								>
									{f.split("/").pop()}
								</Badge>
							))}
							{comparison.common_files.length > 5 && (
								<span className="text-xs text-muted-foreground">
									{t("replay:more", {
										count: comparison.common_files.length - 5,
									})}
								</span>
							)}
						</div>
					</div>
					<div>
						<Label className="text-xs text-muted-foreground">
							{t("replay:onlyInA")}
						</Label>
						<div className="mt-1 space-y-0.5">
							{comparison.unique_files_a.slice(0, 5).map((f) => (
								<Badge
									key={f}
									variant="outline"
									className="text-xs block truncate text-orange-500"
								>
									{f.split("/").pop()}
								</Badge>
							))}
						</div>
					</div>
					<div>
						<Label className="text-xs text-muted-foreground">
							{t("replay:onlyInB")}
						</Label>
						<div className="mt-1 space-y-0.5">
							{comparison.unique_files_b.slice(0, 5).map((f) => (
								<Badge
									key={f}
									variant="outline"
									className="text-xs block truncate text-blue-500"
								>
									{f.split("/").pop()}
								</Badge>
							))}
						</div>
					</div>
				</div>
			</CardContent>
		</Card>
	);
};

/** Debug / breakpoints panel */
const DebugPanel: React.FC<{
	sessionId: string;
	breakpoints: Array<{
		id: string;
		breakpoint_type: string;
		condition: string;
		description: string;
		enabled: boolean;
		hit_count: number;
	}>;
	onAdd: (type: string, condition: string, desc: string) => void;
	onRemove: (id: string) => void;
	// biome-ignore lint/correctness/noUnusedFunctionParameters: parameter kept for API compatibility
}> = ({ sessionId, breakpoints, onAdd, onRemove }) => {
	const { t } = useTranslation();
	const [newType, setNewType] = useState("tool_call");
	const [newCondition, setNewCondition] = useState("");
	const [newDesc, setNewDesc] = useState("");

	return (
		<div className="space-y-4">
			{/* Add breakpoint form */}
			<div className="flex items-end gap-2">
				<div className="flex-1">
					<Label className="text-xs">{t("replay:type")}</Label>
					<Select value={newType} onValueChange={setNewType}>
						<SelectTrigger className="h-8 text-xs">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="tool_call">Tool Call</SelectItem>
							<SelectItem value="file_change">File Change</SelectItem>
							<SelectItem value="decision">Decision</SelectItem>
							<SelectItem value="error">Error</SelectItem>
							<SelectItem value="token_threshold">Token Threshold</SelectItem>
							<SelectItem value="step_index">Step Index</SelectItem>
							<SelectItem value="pattern_match">Pattern Match</SelectItem>
						</SelectContent>
					</Select>
				</div>
				<div className="flex-1">
					<Label className="text-xs">{t("replay:condition")}</Label>
					<Input
						className="h-8 text-xs"
						placeholder="e.g. write_file"
						value={newCondition}
						onChange={(e) => setNewCondition(e.target.value)}
					/>
				</div>
				<Button
					size="sm"
					className="h-8"
					onClick={() => {
						onAdd(newType, newCondition, newDesc);
						setNewCondition("");
						setNewDesc("");
					}}
				>
					<Plus className="h-3 w-3 mr-1" /> {t("replay:add")}
				</Button>
			</div>

			{/* Breakpoints list */}
			{breakpoints.length === 0 ? (
				<p className="text-sm text-muted-foreground">
					{t("replay:noBreakpoints")}
				</p>
			) : (
				<div className="space-y-1.5">
					{breakpoints.map((bp) => (
						<div
							key={bp.id}
							className="flex items-center justify-between p-2 rounded border text-sm"
						>
							<div className="flex items-center gap-2">
								<Bug className="h-3.5 w-3.5 text-red-500" />
								<Badge variant="outline" className="text-xs">
									{bp.breakpoint_type}
								</Badge>
								<span className="text-muted-foreground">
									{bp.condition || "(any)"}
								</span>
								{bp.hit_count > 0 && (
									<Badge variant="secondary" className="text-xs">
										{t("replay:hitCount", "hit {{count}}x", {
											count: bp.hit_count,
										})}
									</Badge>
								)}
							</div>
							<Button variant="ghost" size="sm" onClick={() => onRemove(bp.id)}>
								<X className="h-3 w-3" />
							</Button>
						</div>
					))}
				</div>
			)}
		</div>
	);
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

interface AgentReplayDashboardProps {
	sessionId?: string;
	className?: string;
}

export const AgentReplayDashboard: React.FC<AgentReplayDashboardProps> = ({
	sessionId,
	className = "",
}) => {
	const { t } = useTranslation();
	const {
		sessions,
		sessionsLoading,
		activeSession,
		activeSessionLoading,
		currentStepIndex,
		isPlaying,
		playbackSpeed,
		activeTab,
		breakpoints,
		comparison,
		comparisonSessionA,
		comparisonSessionB,
		error,
		fetchSessions,
		loadSession,
		deleteSession,
		closeSession,
		play,
		pause,
		stop,
		stepForward,
		stepBackward,
		goToStep,
		setPlaybackSpeed,
		setActiveTab,
		fetchHeatmap,
		compareSessionsAction,
		clearComparison,
		addBreakpoint,
		removeBreakpoint,
	} = useAgentReplayStore();

	const [isFullscreen, setIsFullscreen] = useState(false);
	const [stepFilter, setStepFilter] = useState<string>("all");
	const [stepSearch, setStepSearch] = useState("");

	// Initialize
	useEffect(() => {
		fetchSessions();
	}, [fetchSessions]);

	useEffect(() => {
		if (sessionId) loadSession(sessionId);
	}, [sessionId, loadSession]);

	// Load heatmap when session loads
	useEffect(() => {
		if (activeSession) {
			fetchHeatmap(activeSession.session_id);
		}
	}, [activeSession?.session_id, fetchHeatmap, activeSession]);

	const currentStep = activeSession?.steps[currentStepIndex] ?? null;

	const filteredSteps = useMemo(() => {
		if (!activeSession) return [];
		let steps = activeSession.steps;
		if (stepFilter !== "all") {
			steps = steps.filter((s) => s.step_type === stepFilter);
		}
		if (stepSearch) {
			const q = stepSearch.toLowerCase();
			steps = steps.filter(
				(s) =>
					s.label.toLowerCase().includes(q) ||
					s.description.toLowerCase().includes(q),
			);
		}
		return steps;
	}, [activeSession, stepFilter, stepSearch]);

	// --- Session list view ---
	if (!activeSession && !activeSessionLoading) {
		return (
			<div className={`h-full ${className}`}>
				<SessionListView
					sessions={sessions}
					loading={sessionsLoading}
					onSelect={(id) => loadSession(id)}
					onDelete={(id) => deleteSession(id)}
					onCompare={(a, b) => compareSessionsAction(a, b)}
				/>
				{comparison && comparisonSessionA && comparisonSessionB && (
					<div className="p-4">
						<ComparisonPanel
							comparison={comparison}
							sessionA={comparisonSessionA}
							sessionB={comparisonSessionB}
							onClose={clearComparison}
						/>
					</div>
				)}
			</div>
		);
	}

	if (activeSessionLoading) {
		return (
			<div className="flex items-center justify-center h-64">
				<Loader2 className="h-8 w-8 animate-spin" />
			</div>
		);
	}

	if (!activeSession) return null;

	// --- Replay viewer ---
	return (
		<div
			className={`flex flex-col h-full ${className} ${isFullscreen ? "fixed inset-0 z-50 bg-background p-4" : ""}`}
		>
			{/* Top bar */}
			<div className="flex items-center justify-between px-4 py-2 border-b shrink-0">
				<div className="flex items-center gap-3">
					<Button variant="ghost" size="sm" onClick={closeSession}>
						<ArrowLeft className="h-4 w-4 mr-1" /> {t("replay:back")}
					</Button>
					<div>
						<h2 className="text-sm font-semibold flex items-center gap-2">
							{activeSession.agent_name}
							<Badge variant="secondary" className="text-xs">
								{activeSession.agent_role}
							</Badge>
							{activeSession.model_label && (
								<Badge variant="outline" className="text-xs">
									{activeSession.model_label}
								</Badge>
							)}
						</h2>
						<p className="text-xs text-muted-foreground truncate max-w-md">
							{activeSession.task_description || "Untitled"}
						</p>
					</div>
				</div>
				<div className="flex items-center gap-3 text-xs text-muted-foreground">
					<span>{activeSession.step_count} steps</span>
					<span>{formatTokens(activeSession.total_tokens)} tokens</span>
					<span>{formatCost(activeSession.total_cost_usd)}</span>
					<span>{formatDuration(activeSession.duration_seconds * 1000)}</span>
					<Button
						variant="outline"
						size="sm"
						onClick={() => setIsFullscreen(!isFullscreen)}
					>
						{isFullscreen ? (
							<Minimize2 className="h-3.5 w-3.5" />
						) : (
							<Maximize2 className="h-3.5 w-3.5" />
						)}
					</Button>
				</div>
			</div>

			{/* Playback controls */}
			<div className="flex items-center gap-3 px-4 py-2 border-b shrink-0">
				<Button
					variant="outline"
					size="sm"
					onClick={stepBackward}
					disabled={currentStepIndex === 0}
				>
					<SkipBack className="h-3.5 w-3.5" />
				</Button>
				<Button size="sm" onClick={isPlaying ? pause : play}>
					{isPlaying ? (
						<Pause className="h-3.5 w-3.5" />
					) : (
						<Play className="h-3.5 w-3.5" />
					)}
				</Button>
				<Button
					variant="outline"
					size="sm"
					onClick={stepForward}
					disabled={currentStepIndex >= activeSession.steps.length - 1}
				>
					<SkipForward className="h-3.5 w-3.5" />
				</Button>
				<Button variant="outline" size="sm" onClick={stop}>
					<RotateCcw className="h-3.5 w-3.5" />
				</Button>

				{/* Slider */}
				<div className="flex-1 flex items-center gap-2">
					<span className="text-xs text-muted-foreground w-16 text-right">
						{currentStepIndex + 1}/{activeSession.steps.length}
					</span>
					<input
						type="range"
						min={0}
						max={activeSession.steps.length - 1}
						value={currentStepIndex}
						onChange={(e) => goToStep(Number.parseInt(e.target.value, 10))}
						className="flex-1"
					/>
				</div>

				{/* Speed */}
				<Select
					value={playbackSpeed.toString()}
					onValueChange={(v) => setPlaybackSpeed(Number.parseFloat(v))}
				>
					<SelectTrigger className="w-16 h-8 text-xs">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						<SelectItem value="0.25">0.25x</SelectItem>
						<SelectItem value="0.5">0.5x</SelectItem>
						<SelectItem value="1">1x</SelectItem>
						<SelectItem value="2">2x</SelectItem>
						<SelectItem value="4">4x</SelectItem>
					</SelectContent>
				</Select>
			</div>

			{/* Error banner */}
			{error && (
				<div className="px-4 py-1.5 bg-destructive/10 text-destructive text-xs">
					{error}
				</div>
			)}

			{/* Main content area */}
			<div className="flex-1 overflow-hidden flex">
				{/* Left: Timeline */}
				<div className="w-[400px] border-r flex flex-col shrink-0">
					<div className="p-2 border-b flex items-center gap-2">
						<div className="relative flex-1">
							<Search className="absolute left-2 top-2 h-3.5 w-3.5 text-muted-foreground" />
							<Input
								className="pl-7 h-7 text-xs"
								placeholder={t("replay:filterSteps")}
								value={stepSearch}
								onChange={(e) => setStepSearch(e.target.value)}
							/>
						</div>
						<Select value={stepFilter} onValueChange={setStepFilter}>
							<SelectTrigger className="w-28 h-7 text-xs">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="all">{t("replay:all")}</SelectItem>
								<SelectItem value="agent_thinking">
									{t("replay:thinking")}
								</SelectItem>
								<SelectItem value="agent_response">
									{t("replay:response")}
								</SelectItem>
								<SelectItem value="tool_call">
									{t("replay:toolCall")}
								</SelectItem>
								<SelectItem value="file_update">
									{t("replay:fileUpdate")}
								</SelectItem>
								<SelectItem value="file_create">
									{t("replay:fileCreate")}
								</SelectItem>
								<SelectItem value="command_run">
									{t("replay:command")}
								</SelectItem>
								<SelectItem value="error">{t("replay:error")}</SelectItem>
								<SelectItem value="decision">{t("replay:decision")}</SelectItem>
							</SelectContent>
						</Select>
					</div>
					<ScrollArea className="flex-1">
						<div className="p-1">
							{filteredSteps.map((step) => (
								// biome-ignore lint/a11y/noStaticElementInteractions: interactive handler is intentional
								// biome-ignore lint/a11y/useKeyWithClickEvents: keyboard events handled elsewhere
								// biome-ignore lint/a11y/noNoninteractiveElementInteractions: selectable step row
								<div
									key={step.id}
									className={`p-2 rounded cursor-pointer transition-colors text-xs mb-0.5 ${
										currentStepIndex === step.step_index
											? "bg-primary/10 border border-primary"
											: "hover:bg-muted border border-transparent"
									}`}
									onClick={() => goToStep(step.step_index)}
								>
									<div className="flex items-center gap-1.5">
										<div
											className={`w-2 h-2 rounded-full shrink-0 ${getStepColor(step.step_type)}`}
										/>
										<span className="text-muted-foreground shrink-0">
											{getStepIcon(step.step_type)}
										</span>
										<span className="font-medium truncate">{step.label}</span>
										{step.is_breakpoint && (
											<Bug className="h-3 w-3 text-red-500 shrink-0" />
										)}
									</div>
									{step.description && step.description !== step.label && (
										<p className="text-muted-foreground truncate mt-0.5 pl-6">
											{step.description}
										</p>
									)}
									<div className="flex items-center gap-2 mt-0.5 pl-6 text-muted-foreground">
										{step.duration_ms > 0 && (
											<span>{formatDuration(step.duration_ms)}</span>
										)}
										{step.input_tokens + step.output_tokens > 0 && (
											<span>
												{formatTokens(step.input_tokens + step.output_tokens)}{" "}
												tok
											</span>
										)}
									</div>
								</div>
							))}
						</div>
					</ScrollArea>
				</div>

				{/* Right: Detail panel with tabs */}
				<div className="flex-1 flex flex-col overflow-hidden">
					<Tabs
						value={activeTab}
						onValueChange={(v) => setActiveTab(v as typeof activeTab)}
						className="flex flex-col h-full"
					>
						<TabsList className="mx-4 mt-2 shrink-0">
							<TabsTrigger value="timeline" className="text-xs">
								<Eye className="h-3.5 w-3.5 mr-1" /> {t("replay:details")}
							</TabsTrigger>
							<TabsTrigger value="diff" className="text-xs">
								<Code className="h-3.5 w-3.5 mr-1" /> {t("replay:diff")}
							</TabsTrigger>
							<TabsTrigger value="heatmap" className="text-xs">
								<Flame className="h-3.5 w-3.5 mr-1" /> {t("replay:heatmap")}
							</TabsTrigger>
							<TabsTrigger value="tokens" className="text-xs">
								<DollarSign className="h-3.5 w-3.5 mr-1" /> {t("replay:tokens")}
							</TabsTrigger>
							<TabsTrigger value="debug" className="text-xs">
								<Bug className="h-3.5 w-3.5 mr-1" /> {t("replay:debug")}
							</TabsTrigger>
							<TabsTrigger value="compare" className="text-xs">
								<GitCompare className="h-3.5 w-3.5 mr-1" />{" "}
								{t("replay:compare")}
							</TabsTrigger>
						</TabsList>

						<div className="flex-1 overflow-auto">
							{/* Step details */}
							<TabsContent value="timeline" className="p-4 space-y-4 mt-0">
								{currentStep ? (
									<>
										<div className="grid grid-cols-2 gap-3">
											<div className="space-y-2">
												<div className="flex justify-between text-sm">
													<Label>Type</Label>
													<Badge variant="secondary">
														{currentStep.step_type}
													</Badge>
												</div>
												<div className="flex justify-between text-sm">
													<Label>Duration</Label>
													<span>{formatDuration(currentStep.duration_ms)}</span>
												</div>
												<div className="flex justify-between text-sm">
													<Label>Tokens</Label>
													<span>
														{formatTokens(currentStep.input_tokens)} in /{" "}
														{formatTokens(currentStep.output_tokens)} out
													</span>
												</div>
												<div className="flex justify-between text-sm">
													<Label>Cost</Label>
													<span>{formatCost(currentStep.cost_usd)}</span>
												</div>
												<div className="flex justify-between text-sm">
													<Label>Cumulative</Label>
													<span>
														{formatTokens(currentStep.cumulative_tokens)} /{" "}
														{formatCost(currentStep.cumulative_cost_usd)}
													</span>
												</div>
											</div>
											<div className="space-y-2">
												{currentStep.tool_name && (
													<div className="flex justify-between text-sm">
														<Label>Tool</Label>
														<Badge variant="outline">
															{currentStep.tool_name}
														</Badge>
													</div>
												)}
												{currentStep.chosen_option && (
													<div className="text-sm">
														<Label>Decision</Label>
														<p className="text-muted-foreground mt-0.5">
															{currentStep.chosen_option}
														</p>
													</div>
												)}
											</div>
										</div>

										{/* Reasoning */}
										{currentStep.reasoning && (
											<div>
												<Label className="text-xs text-muted-foreground">
													Reasoning
												</Label>
												<div className="mt-1 p-3 bg-muted rounded-lg">
													<pre className="text-xs whitespace-pre-wrap">
														{currentStep.reasoning}
													</pre>
												</div>
											</div>
										)}

										{/* Tool input/output */}
										{currentStep.tool_input && (
											<div>
												<Label className="text-xs text-muted-foreground">
													Tool Input
												</Label>
												<div className="mt-1 p-3 bg-muted rounded-lg">
													<pre className="text-xs whitespace-pre-wrap overflow-auto max-h-40">
														{JSON.stringify(currentStep.tool_input, null, 2)}
													</pre>
												</div>
											</div>
										)}
										{currentStep.tool_output && (
											<div>
												<Label className="text-xs text-muted-foreground">
													Tool Output
												</Label>
												<div className="mt-1 p-3 bg-muted rounded-lg">
													<pre className="text-xs whitespace-pre-wrap overflow-auto max-h-40">
														{currentStep.tool_output}
													</pre>
												</div>
											</div>
										)}

										{/* Decision options */}
										{currentStep.options_considered.length > 0 && (
											<div>
												<Label className="text-xs text-muted-foreground">
													Options Considered
												</Label>
												<div className="mt-1 space-y-1">
													{currentStep.options_considered.map((opt) => (
														<div
															key={`opt-${opt}`}
															className={`p-2 rounded text-xs ${
																opt === currentStep.chosen_option
																	? "bg-primary/10 border border-primary"
																	: "bg-muted"
															}`}
														>
															{opt === currentStep.chosen_option && (
																<CheckCircle className="h-3 w-3 inline mr-1 text-primary" />
															)}
															{opt}
														</div>
													))}
												</div>
											</div>
										)}
									</>
								) : (
									<p className="text-sm text-muted-foreground">
										Select a step from the timeline.
									</p>
								)}
							</TabsContent>

							{/* Diff view */}
							<TabsContent value="diff" className="p-4 space-y-4 mt-0">
								{currentStep?.file_diffs &&
								currentStep.file_diffs.length > 0 ? (
									currentStep.file_diffs.map((diff) => {
										const getVariant = (
											operation: string,
										): "default" | "destructive" | "secondary" => {
											if (operation === "create") return "default";
											if (operation === "delete") return "destructive";
											return "secondary";
										};

										const getLineClassName = (line: string): string => {
											if (line.startsWith("+"))
												return "text-green-600 bg-green-500/10";
											if (line.startsWith("-"))
												return "text-red-600 bg-red-500/10";
											return "";
										};

										return (
											<Card key={`diff-${diff.file_path}`}>
												<CardHeader className="py-2 px-3">
													<div className="flex items-center justify-between">
														<span className="text-sm font-mono">
															{diff.file_path}
														</span>
														<Badge variant={getVariant(diff.operation)}>
															{diff.operation}
														</Badge>
													</div>
												</CardHeader>
												<CardContent className="py-2 px-3">
													{diff.diff_lines && diff.diff_lines.length > 0 ? (
														<pre className="text-xs font-mono overflow-auto max-h-60 bg-muted p-2 rounded">
															{diff.diff_lines.map((line) => (
																<div
																	key={`line-${line}`}
																	className={getLineClassName(line)}
																>
																	{line}
																</div>
															))}
														</pre>
													) : (
														<p className="text-xs text-muted-foreground">
															{diff.line_count_before} → {diff.line_count_after}{" "}
															lines
														</p>
													)}
												</CardContent>
											</Card>
										);
									})
								) : (
									<p className="text-sm text-muted-foreground">
										{t("replay:noFileChangesAtStep")}
									</p>
								)}
							</TabsContent>

							{/* Heatmap */}
							<TabsContent value="heatmap" className="p-4 mt-0">
								<Card>
									<CardHeader>
										<CardTitle className="text-sm flex items-center gap-2">
											<Flame className="h-4 w-4" />{" "}
											{t("replay:fileActivityHeatmap")}
										</CardTitle>
										<CardDescription className="text-xs">
											Files most frequently touched by the agent
										</CardDescription>
									</CardHeader>
									<CardContent>
										<FileHeatmap heatmap={activeSession.file_heatmap || {}} />
									</CardContent>
								</Card>

								{/* Tool usage */}
								<Card className="mt-4">
									<CardHeader>
										<CardTitle className="text-sm flex items-center gap-2">
											<Wrench className="h-4 w-4" /> Tool Usage
										</CardTitle>
									</CardHeader>
									<CardContent>
										<div className="space-y-1.5">
											{Object.entries(activeSession.tool_usage_stats || {}).map(
												([tool, count]) => (
													<div
														key={tool}
														className="flex items-center justify-between text-sm"
													>
														<Badge variant="outline">{tool}</Badge>
														<span className="text-muted-foreground">
															{count}x
														</span>
													</div>
												),
											)}
										</div>
									</CardContent>
								</Card>
							</TabsContent>

							{/* Token timeline */}
							<TabsContent value="tokens" className="p-4 mt-0">
								<Card>
									<CardHeader>
										<CardTitle className="text-sm flex items-center gap-2">
											<DollarSign className="h-4 w-4" />{" "}
											{t("replay:tokenConsumption")}
										</CardTitle>
										<CardDescription className="text-xs">
											{t("replay:total", "{{tokens}} total • {{cost}}", {
												tokens: formatTokens(activeSession.total_tokens),
												cost: formatCost(activeSession.total_cost_usd),
											})}
										</CardDescription>
									</CardHeader>
									<CardContent>
										<TokenTimeline
											timeline={activeSession.token_timeline || []}
											currentIndex={currentStepIndex}
										/>
									</CardContent>
								</Card>
							</TabsContent>

							{/* Debug */}
							<TabsContent value="debug" className="p-4 mt-0">
								<Card>
									<CardHeader>
										<CardTitle className="text-sm flex items-center gap-2">
											<Bug className="h-4 w-4" /> Breakpoints
										</CardTitle>
										<CardDescription className="text-xs">
											Set breakpoints to pause replay at specific events
										</CardDescription>
									</CardHeader>
									<CardContent>
										<DebugPanel
											sessionId={activeSession.session_id}
											breakpoints={breakpoints}
											onAdd={(type, condition, desc) =>
												addBreakpoint(
													activeSession.session_id,
													type,
													condition,
													desc,
												)
											}
											onRemove={(id) =>
												removeBreakpoint(activeSession.session_id, id)
											}
										/>
									</CardContent>
								</Card>
							</TabsContent>

							{/* Compare */}
							<TabsContent value="compare" className="p-4 mt-0">
								{comparison && comparisonSessionA && comparisonSessionB ? (
									<ComparisonPanel
										comparison={comparison}
										sessionA={comparisonSessionA}
										sessionB={comparisonSessionB}
										onClose={clearComparison}
									/>
								) : (
									<Card>
										<CardContent className="py-8 text-center">
											<GitCompare className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
											<p className="text-sm text-muted-foreground">
												Select two sessions from the session list to compare
												them side by side.
											</p>
											<Button
												variant="outline"
												size="sm"
												className="mt-3"
												onClick={closeSession}
											>
												<ArrowLeft className="h-3.5 w-3.5 mr-1" /> Go to session
												list
											</Button>
										</CardContent>
									</Card>
								)}
							</TabsContent>
						</div>
					</Tabs>
				</div>
			</div>
		</div>
	);
};
