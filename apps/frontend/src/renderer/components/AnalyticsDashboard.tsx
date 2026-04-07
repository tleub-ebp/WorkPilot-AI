import {
	Activity,
	AlertTriangle,
	BarChart3,
	CheckCircle2,
	Coins,
	DollarSign,
	FolderOpen,
	GitMerge,
	Loader2,
	RefreshCw,
	Target,
	TrendingDown,
	TrendingUp,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { ScrollArea } from "./ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CostSummaryData {
	total_cost: number;
	cost_by_provider: Record<string, number>;
	cost_by_model: Record<string, number>;
	total_tokens: number;
	tokens_input: number;
	tokens_output: number;
	period_days: number;
	daily_avg: number;
	trend_pct: number;
}

interface SnapshotData {
	tasks_by_status: Record<string, number>;
	avg_completion_by_complexity: Record<string, number>;
	qa_first_pass_rate: number;
	qa_avg_score: number;
	total_tokens: number;
	tokens_by_provider: Record<string, number>;
	total_cost: number;
	cost_by_model: Record<string, number>;
	merge_auto_count: number;
	merge_manual_count: number;
}

interface AnalyticsDashboardProps {
	readonly className?: string;
	readonly projectPath?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTokens(n: number): string {
	if (n < 1000) return n.toString();
	if (n < 1_000_000) return `${(n / 1000).toFixed(1)}K`;
	return `${(n / 1_000_000).toFixed(2)}M`;
}

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------

function KpiCard({
	title,
	value,
	subtitle,
	icon,
	className,
}: {
	readonly title: string;
	readonly value: string;
	readonly subtitle?: string;
	readonly icon: React.ReactNode;
	readonly className?: string;
}) {
	return (
		<Card className={cn("relative overflow-hidden", className)}>
			<CardContent className="p-5">
				<div className="flex items-start justify-between">
					<div className="flex-1 min-w-0 space-y-1">
						<p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
							{title}
						</p>
						<p className="text-2xl font-bold text-foreground">{value}</p>
						{subtitle && (
							<p className="text-xs text-muted-foreground">{subtitle}</p>
						)}
					</div>
					<div className="p-2.5 bg-muted rounded-lg">{icon}</div>
				</div>
			</CardContent>
		</Card>
	);
}

// ---------------------------------------------------------------------------
// Breakdown bar list (provider / model)
// ---------------------------------------------------------------------------

function BreakdownList({
	data,
	formatValue,
}: {
	readonly data: Record<string, number>;
	readonly formatValue: (v: number) => string;
}) {
	const entries = Object.entries(data)
		.sort(([, a], [, b]) => b - a)
		.filter(([, v]) => v > 0);
	const total = entries.reduce((s, [, v]) => s + v, 0);

	if (entries.length === 0) {
		return <p className="text-xs text-muted-foreground">—</p>;
	}

	const colors = [
		"bg-primary",
		"bg-blue-500",
		"bg-emerald-500",
		"bg-amber-500",
		"bg-purple-500",
		"bg-pink-500",
	];

	return (
		<div className="space-y-2.5">
			{entries.map(([name, value], idx) => {
				const pct = total > 0 ? (value / total) * 100 : 0;
				return (
					<div key={name} className="space-y-1">
						<div className="flex items-center justify-between text-xs">
							<span className="text-foreground font-medium capitalize truncate">
								{name}
							</span>
							<span className="text-muted-foreground shrink-0 ml-2">
								{formatValue(value)} ({pct.toFixed(0)}%)
							</span>
						</div>
						<div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
							<div
								className={cn(
									"h-full rounded-full transition-all",
									colors[idx % colors.length],
								)}
								style={{ width: `${pct}%` }}
							/>
						</div>
					</div>
				);
			})}
		</div>
	);
}

// ---------------------------------------------------------------------------
// Status bar (task statuses)
// ---------------------------------------------------------------------------

function StatusBar({ data }: { readonly data: Record<string, number> }) {
	const { t } = useTranslation("analytics");
	const total = Object.values(data).reduce((a, b) => a + b, 0);

	if (total === 0) {
		return (
			<p className="text-xs text-muted-foreground">{t("status.noData")}</p>
		);
	}

	const statusColors: Record<string, string> = {
		completed: "bg-emerald-500",
		complete: "bg-emerald-500",
		in_progress: "bg-blue-500",
		pending: "bg-amber-500",
		failed: "bg-red-500",
		cancelled: "bg-gray-400",
	};

	return (
		<div className="space-y-3">
			<div className="flex h-3 w-full overflow-hidden rounded-full bg-secondary">
				{Object.entries(data).map(([status, count]) => {
					const pct = (count / total) * 100;
					if (pct === 0) return null;
					return (
						<div
							key={status}
							className={cn(
								"h-full transition-all",
								statusColors[status] ?? "bg-gray-300",
							)}
							style={{ width: `${pct}%` }}
							title={`${status}: ${count}`}
						/>
					);
				})}
			</div>
			<div className="flex flex-wrap gap-3">
				{Object.entries(data).map(([status, count]) => (
					<div key={status} className="flex items-center gap-1.5 text-xs">
						<div
							className={cn(
								"h-2 w-2 rounded-full",
								statusColors[status] ?? "bg-gray-300",
							)}
						/>
						<span className="text-muted-foreground capitalize">
							{status.replace("_", " ")}
						</span>
						<span className="font-semibold text-foreground">{count}</span>
					</div>
				))}
			</div>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

function formatDuration(seconds: number): string {
	if (seconds < 60) {
		return `${seconds.toFixed(0)}s`;
	} else if (seconds < 3600) {
		return `${(seconds / 60).toFixed(1)}m`;
	} else {
		return `${(seconds / 3600).toFixed(1)}h`;
	}
}

function getTokensByProviderContent(
	sn: SnapshotData | null,
	cs: CostSummaryData | null,
	t: (key: string) => string,
) {
	if (sn && Object.keys(sn.tokens_by_provider).length > 0) {
		return (
			<BreakdownList
				data={sn.tokens_by_provider}
				formatValue={(v) => formatTokens(v)}
			/>
		);
	} else if (cs) {
		return (
			<BreakdownList
				data={cs.cost_by_provider}
				formatValue={(_v) => formatTokens(cs.total_tokens)}
			/>
		);
	} else {
		return (
			<p className="text-xs text-muted-foreground">{t("status.noData")}</p>
		);
	}
}

function getTrendColor(trendPct: number): string {
	if (trendPct > 20) {
		return "text-red-500";
	} else if (trendPct > 0) {
		return "text-amber-500";
	} else {
		return "text-emerald-500";
	}
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function AnalyticsDashboard({
	className,
	projectPath,
}: AnalyticsDashboardProps) {
	const { t } = useTranslation("analytics");
	const [costSummary, setCostSummary] = useState<CostSummaryData | null>(null);
	const [snapshot, setSnapshot] = useState<SnapshotData | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchAnalytics = useCallback(async () => {
		if (!projectPath) {
			setLoading(false);
			return;
		}
		setLoading(true);
		setError(null);
		try {
			const [costRes, snapRes] = await Promise.allSettled([
				globalThis.electronAPI.getCostSummary(projectPath),
				globalThis.electronAPI.getDashboardSnapshot(projectPath),
			]);

			if (costRes.status === "fulfilled" && costRes.value.success) {
				setCostSummary(costRes.value.summary ?? null);
			}
			if (snapRes.status === "fulfilled" && snapRes.value.success) {
				setSnapshot(snapRes.value.snapshot ?? null);
			}

			const bothFailed =
				(costRes.status === "rejected" || !costRes.value?.success) &&
				(snapRes.status === "rejected" || !snapRes.value?.success);
			if (bothFailed) setError(t("status.error"));
		} catch (e) {
			setError(e instanceof Error ? e.message : t("status.error"));
		} finally {
			setLoading(false);
		}
	}, [projectPath, t]);

	useEffect(() => {
		fetchAnalytics();
	}, [fetchAnalytics]);

	// ── No project selected ────────────────────────────────────────────────
	if (!projectPath) {
		return (
			<div className="flex items-center justify-center h-96">
				<div className="flex flex-col items-center gap-3 text-muted-foreground">
					<FolderOpen className="h-10 w-10" />
					<p className="text-sm">{t("empty.noProject")}</p>
				</div>
			</div>
		);
	}

	// ── Loading ────────────────────────────────────────────────────────────
	if (loading) {
		return (
			<div className="flex items-center justify-center h-96">
				<div className="flex items-center space-x-2">
					<Loader2 className="h-6 w-6 animate-spin" />
					<span className="text-sm text-muted-foreground">
						{t("status.loading")}
					</span>
				</div>
			</div>
		);
	}

	// ── Error ──────────────────────────────────────────────────────────────
	if (error && !costSummary && !snapshot) {
		return (
			<div className="flex flex-col items-center justify-center h-96 gap-4 text-muted-foreground">
				<AlertTriangle className="h-8 w-8" />
				<p className="text-sm">{error}</p>
				<Button variant="outline" size="sm" onClick={fetchAnalytics}>
					<RefreshCw className="h-3.5 w-3.5 mr-2" />
					{t("status.retry")}
				</Button>
			</div>
		);
	}

	// ── Derived values ─────────────────────────────────────────────────────
	const cs = costSummary;
	const sn = snapshot;

	const totalTasks = sn
		? Object.values(sn.tasks_by_status).reduce((a, b) => a + b, 0)
		: 0;
	const completedTasks = sn
		? (sn.tasks_by_status.completed ?? sn.tasks_by_status.complete ?? 0)
		: 0;
	const successRate = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;
	const totalCost = cs?.total_cost ?? sn?.total_cost ?? 0;
	const totalTokens = cs?.total_tokens ?? sn?.total_tokens ?? 0;
	const _qaPassRate = sn?.qa_first_pass_rate ?? 0;

	const trendPct = cs?.trend_pct ?? 0;
	const TrendIcon = trendPct >= 0 ? TrendingUp : TrendingDown;
	const trendColor = getTrendColor(trendPct);

	return (
		<ScrollArea className={cn("h-full", className)}>
			<div className="p-6 space-y-6 max-w-5xl mx-auto">
				{/* Header */}
				<div className="flex items-center justify-between">
					<div>
						<h2 className="text-2xl font-bold tracking-tight text-foreground">
							{t("title")}
						</h2>
						<p className="text-sm text-muted-foreground">{t("subtitle")}</p>
					</div>
					<Button onClick={fetchAnalytics} variant="outline" size="sm">
						<RefreshCw className="h-3.5 w-3.5 mr-2" />
						{t("actions.refresh")}
					</Button>
				</div>

				{/* KPI cards */}
				<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
					<KpiCard
						title={t("kpis.totalBuilds.title")}
						value={String(totalTasks)}
						subtitle={`${completedTasks} ${t("kpis.successfulBuilds.title").toLowerCase()}`}
						icon={<BarChart3 className="h-5 w-5 text-blue-500" />}
					/>
					<KpiCard
						title={t("kpis.successRate.title")}
						value={`${successRate.toFixed(1)}%`}
						subtitle={t("kpis.successRate.description")}
						icon={<CheckCircle2 className="h-5 w-5 text-green-500" />}
					/>
					<KpiCard
						title={t("kpis.totalTokens.title")}
						value={formatTokens(totalTokens)}
						subtitle={t("kpis.totalTokens.description")}
						icon={<Coins className="h-5 w-5 text-orange-500" />}
					/>
					<KpiCard
						title={t("kpis.totalCost.title")}
						value={`$${totalCost.toFixed(4)}`}
						subtitle={
							cs
								? `${t("fields.dailyAvg")}: $${cs.daily_avg.toFixed(4)}`
								: t("kpis.totalCost.description")
						}
						icon={<DollarSign className="h-5 w-5 text-purple-500" />}
					/>
				</div>

				{/* Tabs */}
				<Tabs defaultValue="overview" className="space-y-4">
					<TabsList>
						<TabsTrigger value="overview">{t("tabs.overview")}</TabsTrigger>
						<TabsTrigger value="costs">{t("tabs.costs")}</TabsTrigger>
						<TabsTrigger value="performance">
							{t("tabs.performance")}
						</TabsTrigger>
					</TabsList>

					{/* ── Overview tab ──────────────────────────────────────────── */}
					<TabsContent value="overview" className="space-y-4">
						<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
							{/* Task status */}
							<Card>
								<CardHeader className="pb-3">
									<CardTitle className="flex items-center gap-2 text-sm font-semibold">
										<Target className="h-4 w-4" />
										{t("sections.tasksByStatus")}
									</CardTitle>
								</CardHeader>
								<CardContent>
									{sn ? (
										<StatusBar data={sn.tasks_by_status} />
									) : (
										<p className="text-xs text-muted-foreground">
											{t("status.noData")}
										</p>
									)}
								</CardContent>
							</Card>

							{/* QA + Merge stats */}
							<Card>
								<CardHeader className="pb-3">
									<CardTitle className="flex items-center gap-2 text-sm font-semibold">
										<Activity className="h-4 w-4" />
										{t("sections.qaMetrics")}
									</CardTitle>
								</CardHeader>
								<CardContent>
									{sn ? (
										<div className="space-y-4">
											<div className="space-y-1">
												<div className="flex justify-between text-xs">
													<span className="text-muted-foreground">
														{t("fields.qaPassRate")}
													</span>
													<span className="font-semibold text-foreground">
														{sn.qa_first_pass_rate.toFixed(1)}%
													</span>
												</div>
												<div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
													<div
														className="h-full rounded-full bg-emerald-500 transition-all"
														style={{
															width: `${Math.min(sn.qa_first_pass_rate, 100)}%`,
														}}
													/>
												</div>
											</div>
											<div className="grid grid-cols-2 gap-3 pt-1">
												<div className="text-xs">
													<p className="text-muted-foreground">
														{t("fields.mergeAuto")}
													</p>
													<p className="font-semibold text-foreground text-base">
														{sn.merge_auto_count}
													</p>
												</div>
												<div className="text-xs">
													<p className="text-muted-foreground">
														{t("fields.mergeManual")}
													</p>
													<p className="font-semibold text-foreground text-base">
														{sn.merge_manual_count}
													</p>
												</div>
											</div>
										</div>
									) : (
										<p className="text-xs text-muted-foreground">
											{t("status.noData")}
										</p>
									)}
								</CardContent>
							</Card>
						</div>
					</TabsContent>

					{/* ── Costs tab ─────────────────────────────────────────────── */}
					<TabsContent value="costs" className="space-y-4">
						<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
							{/* Cost by provider */}
							<Card>
								<CardHeader className="pb-3">
									<CardTitle className="text-sm font-semibold">
										{t("sections.costByProvider")}
									</CardTitle>
								</CardHeader>
								<CardContent>
									{cs ? (
										<BreakdownList
											data={cs.cost_by_provider}
											formatValue={(v) => `$${v.toFixed(4)}`}
										/>
									) : (
										<p className="text-xs text-muted-foreground">
											{t("status.noData")}
										</p>
									)}
								</CardContent>
							</Card>

							{/* Cost by model */}
							<Card>
								<CardHeader className="pb-3">
									<CardTitle className="text-sm font-semibold">
										{t("sections.costByModel")}
									</CardTitle>
								</CardHeader>
								<CardContent>
									{cs ? (
										<BreakdownList
											data={cs.cost_by_model}
											formatValue={(v) => `$${v.toFixed(4)}`}
										/>
									) : (
										<p className="text-xs text-muted-foreground">
											{t("status.noData")}
										</p>
									)}
								</CardContent>
							</Card>
						</div>

						{/* Daily avg + trend card */}
						{cs && (
							<Card>
								<CardContent className="p-5">
									<div className="flex items-center justify-between">
										<div>
											<p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
												{t("fields.dailyAvg")}
											</p>
											<p className="mt-1 text-xl font-bold text-foreground">
												${cs.daily_avg.toFixed(4)}
											</p>
											<p className="text-xs text-muted-foreground">
												{t("fields.overDays", { days: cs.period_days })}
											</p>
										</div>
										<div
											className={cn(
												"flex items-center gap-1 text-sm font-medium",
												trendColor,
											)}
										>
											<TrendIcon className="h-4 w-4" />
											<span>
												{trendPct >= 0 ? "+" : ""}
												{trendPct.toFixed(0)}% {t("fields.trend")}
											</span>
										</div>
									</div>
								</CardContent>
							</Card>
						)}
					</TabsContent>

					{/* ── Performance tab ────────────────────────────────────────── */}
					<TabsContent value="performance" className="space-y-4">
						<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
							{/* Tokens by provider */}
							<Card>
								<CardHeader className="pb-3">
									<CardTitle className="flex items-center gap-2 text-sm font-semibold">
										<Zap className="h-4 w-4" />
										{t("sections.tokensByProvider")}
									</CardTitle>
								</CardHeader>
								<CardContent>
									{getTokensByProviderContent(sn, cs, t)}
								</CardContent>
							</Card>

							{/* Completion by complexity */}
							<Card>
								<CardHeader className="pb-3">
									<CardTitle className="flex items-center gap-2 text-sm font-semibold">
										<GitMerge className="h-4 w-4" />
										{t("sections.completionByComplexity")}
									</CardTitle>
								</CardHeader>
								<CardContent>
									{sn &&
									Object.keys(sn.avg_completion_by_complexity).length > 0 ? (
										<div className="space-y-2">
											{Object.entries(sn.avg_completion_by_complexity)
												.sort(([, a], [, b]) => a - b)
												.map(([complexity, avgSecs]) => (
													<div
														key={complexity}
														className="flex items-center justify-between text-xs"
													>
														<span className="text-foreground capitalize font-medium">
															{complexity}
														</span>
														<span className="text-muted-foreground">
															{formatDuration(avgSecs)}
														</span>
													</div>
												))}
										</div>
									) : (
										<p className="text-xs text-muted-foreground">
											{t("status.noData")}
										</p>
									)}
								</CardContent>
							</Card>
						</div>

						{/* Input / Output tokens split */}
						{cs && (
							<Card>
								<CardContent className="p-5">
									<p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
										{t("sections.tokenSplit")}
									</p>
									<div className="grid grid-cols-3 gap-4 text-sm">
										<div>
											<p className="text-muted-foreground text-xs">
												{t("fields.totalTokens")}
											</p>
											<p className="font-bold text-foreground">
												{formatTokens(cs.total_tokens)}
											</p>
										</div>
										<div>
											<p className="text-muted-foreground text-xs">
												{t("fields.inputTokens")}
											</p>
											<p className="font-bold text-foreground">
												{formatTokens(cs.tokens_input)}
											</p>
										</div>
										<div>
											<p className="text-muted-foreground text-xs">
												{t("fields.outputTokens")}
											</p>
											<p className="font-bold text-foreground">
												{formatTokens(cs.tokens_output)}
											</p>
										</div>
									</div>
								</CardContent>
							</Card>
						)}
					</TabsContent>
				</Tabs>
			</div>
		</ScrollArea>
	);
}
