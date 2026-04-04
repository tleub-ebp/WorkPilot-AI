/**
 * Mission Control Dashboard — NASA-style Multi-Agent Orchestration Hub.
 *
 * Main component that provides:
 * - Session header with global stats (total agents, tokens, cost, elapsed)
 * - Agent grid with individual panels per agent
 * - Add agent dialog with provider/model selection
 * - Decision tree viewer for selected agent
 * - Live event log
 */

import {
	Activity,
	AlertTriangle,
	Brain,
	Clock,
	Cpu,
	DollarSign,
	GitBranch,
	Loader2,
	Plus,
	Power,
	PowerOff,
	RefreshCw,
	Rocket,
	Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMissionControlStore } from "../../stores/mission-control-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { ScrollArea } from "../ui/scroll-area";
import {
	AddAgentDialog,
	AgentEventLog,
	AgentPanel,
	DecisionTreeViewer,
} from "./index";

export function MissionControlDashboard() {
	const { t } = useTranslation(["missionControl", "common"]);
	const {
		session,
		isActive,
		agents,
		selectedAgentId,
		decisionTrees,
		events,
		isLoading,
		error,
		startSession,
		stopSession,
		fetchState,
		createAgent,
		removeAgent,
		startAgent,
		pauseAgent,
		resumeAgent,
		stopAgent,
		selectAgent,
		startPolling,
		stopPolling,
		updateAgentConfig,
	} = useMissionControlStore();

	const [showAddAgent, setShowAddAgent] = useState(false);

	// Auto-start polling when session is active
	useEffect(() => {
		if (isActive) {
			startPolling();
		}
		return () => {
			stopPolling();
		};
	}, [isActive, startPolling, stopPolling]);

	const selectedAgent = useMemo(
		() => agents.find((a) => a.id === selectedAgentId) ?? null,
		[agents, selectedAgentId],
	);

	const selectedTree = useMemo(
		() => (selectedAgentId ? (decisionTrees[selectedAgentId] ?? null) : null),
		[selectedAgentId, decisionTrees],
	);

	const runningCount = agents.filter((a) => a.status === "running").length;
	const totalTokens = agents.reduce((sum, a) => sum + a.tokens.total_tokens, 0);
	const totalCost = agents.reduce(
		(sum, a) => sum + a.tokens.estimated_cost_usd,
		0,
	);

	const handleAddAgent = async (
		name: string,
		role: string,
		provider: string,
		model: string,
		modelLabel: string,
	) => {
		await createAgent(name, role, provider, model, modelLabel);
		setShowAddAgent(false);
	};

	// ---------------------------------------------------------------
	// Inactive state — show launch screen
	// ---------------------------------------------------------------
	if (!isActive) {
		return (
			<div className="flex flex-col items-center justify-center h-full gap-8 p-8">
				<div className="flex flex-col items-center gap-4 max-w-lg text-center">
					<div className="relative">
						<div className="absolute inset-0 bg-primary/20 blur-3xl rounded-full" />
						<div className="relative bg-linear-to-br from-primary/10 to-primary/5 border border-primary/20 rounded-3xl p-8">
							<Rocket className="h-16 w-16 text-primary" />
						</div>
					</div>
					<h1 className="text-3xl font-bold bg-linear-to-r from-primary to-primary/60 bg-clip-text text-transparent">
						Mission Control
					</h1>
					<p className="text-muted-foreground text-lg">
						{t(
							"missionControl:launchDescription",
							"Multi-Agent Orchestration Hub — Orchestrate multiple AI agents simultaneously with full visibility on reasoning, files, and token consumption.",
						)}
					</p>
					<div className="grid grid-cols-2 gap-3 w-full max-w-sm text-sm text-muted-foreground">
						<div className="flex items-center gap-2 bg-card/50 rounded-lg p-3 border border-border/50">
							<Users className="h-4 w-4 text-primary" />
							<span>
								{t("missionControl:featureMultiAgent", "Multi-Agent")}
							</span>
						</div>
						<div className="flex items-center gap-2 bg-card/50 rounded-lg p-3 border border-border/50">
							<Brain className="h-4 w-4 text-primary" />
							<span>
								{t("missionControl:featureModelMixing", "Model Mixing")}
							</span>
						</div>
						<div className="flex items-center gap-2 bg-card/50 rounded-lg p-3 border border-border/50">
							<GitBranch className="h-4 w-4 text-primary" />
							<span>
								{t("missionControl:featureDecisionTree", "Decision Tree")}
							</span>
						</div>
						<div className="flex items-center gap-2 bg-card/50 rounded-lg p-3 border border-border/50">
							<Activity className="h-4 w-4 text-primary" />
							<span>{t("missionControl:featureLiveView", "Live View")}</span>
						</div>
					</div>
					<Button
						size="lg"
						onClick={() => startSession()}
						disabled={isLoading}
						className="mt-4 gap-2 text-base px-8"
					>
						{isLoading ? (
							<Loader2 className="h-5 w-5 animate-spin" />
						) : (
							<Power className="h-5 w-5" />
						)}
						{t("missionControl:launchSession", "Launch Mission Control")}
					</Button>
				</div>
			</div>
		);
	}

	// ---------------------------------------------------------------
	// Active state — full dashboard
	// ---------------------------------------------------------------
	return (
		<ScrollArea className="h-full">
			<div className="p-4 space-y-4 max-w-[1800px] mx-auto">
				{/* Header */}
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-3">
						<div className="bg-linear-to-br from-primary/20 to-primary/5 border border-primary/30 rounded-xl p-2.5">
							<Rocket className="h-6 w-6 text-primary" />
						</div>
						<div>
							<h1 className="text-xl font-bold text-foreground">
								Mission Control
							</h1>
							<p className="text-xs text-muted-foreground">
								{session?.session_id ?? "—"}
							</p>
						</div>
					</div>
					<div className="flex items-center gap-2">
						<Button
							variant="outline"
							size="sm"
							onClick={() => fetchState()}
							className="gap-1.5"
						>
							<RefreshCw className="h-3.5 w-3.5" />
							{t("common:refresh", "Refresh")}
						</Button>
						<Button
							variant="outline"
							size="sm"
							onClick={() => setShowAddAgent(true)}
							className="gap-1.5"
						>
							<Plus className="h-3.5 w-3.5" />
							{t("missionControl:addAgent", "Add Agent")}
						</Button>
						<Button
							variant="destructive"
							size="sm"
							onClick={() => stopSession()}
							className="gap-1.5"
						>
							<PowerOff className="h-3.5 w-3.5" />
							{t("missionControl:stopSession", "Stop")}
						</Button>
					</div>
				</div>

				{/* Global Stats Bar */}
				<div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
					<Card className="border-border/50">
						<CardContent className="p-3 flex items-center gap-3">
							<div className="bg-blue-500/10 rounded-lg p-2">
								<Users className="h-4 w-4 text-blue-500" />
							</div>
							<div>
								<p className="text-xs text-muted-foreground">
									{t("missionControl:statAgents", "Agents")}
								</p>
								<p className="text-lg font-bold">
									{runningCount}
									<span className="text-sm font-normal text-muted-foreground">
										/{agents.length}
									</span>
								</p>
							</div>
						</CardContent>
					</Card>
					<Card className="border-border/50">
						<CardContent className="p-3 flex items-center gap-3">
							<div className="bg-purple-500/10 rounded-lg p-2">
								<Cpu className="h-4 w-4 text-purple-500" />
							</div>
							<div>
								<p className="text-xs text-muted-foreground">
									{t("missionControl:statTokens", "Tokens")}
								</p>
								<p className="text-lg font-bold">
									{totalTokens.toLocaleString()}
								</p>
							</div>
						</CardContent>
					</Card>
					<Card className="border-border/50">
						<CardContent className="p-3 flex items-center gap-3">
							<div className="bg-green-500/10 rounded-lg p-2">
								<DollarSign className="h-4 w-4 text-green-500" />
							</div>
							<div>
								<p className="text-xs text-muted-foreground">
									{t("missionControl:statCost", "Cost")}
								</p>
								<p className="text-lg font-bold">${totalCost.toFixed(4)}</p>
							</div>
						</CardContent>
					</Card>
					<Card className="border-border/50">
						<CardContent className="p-3 flex items-center gap-3">
							<div className="bg-orange-500/10 rounded-lg p-2">
								<Clock className="h-4 w-4 text-orange-500" />
							</div>
							<div>
								<p className="text-xs text-muted-foreground">
									{t("missionControl:statElapsed", "Elapsed")}
								</p>
								<p className="text-lg font-bold">
									{formatElapsed(session?.elapsed_seconds ?? 0)}
								</p>
							</div>
						</CardContent>
					</Card>
				</div>

				{/* Error banner */}
				{error && (
					<div className="flex items-center gap-2 bg-destructive/10 border border-destructive/30 rounded-lg p-3 text-sm text-destructive">
						<AlertTriangle className="h-4 w-4 shrink-0" />
						{error}
					</div>
				)}

				{/* Agent Grid */}
				{agents.length === 0 ? (
					<Card className="border-dashed border-2 border-border/50">
						<CardContent className="flex flex-col items-center justify-center py-12 gap-4 text-muted-foreground">
							<Users className="h-10 w-10 opacity-50" />
							<p className="text-sm">
								{t(
									"missionControl:noAgents",
									"No agents yet. Add your first agent to get started.",
								)}
							</p>
							<Button
								variant="outline"
								size="sm"
								onClick={() => setShowAddAgent(true)}
								className="gap-1.5"
							>
								<Plus className="h-3.5 w-3.5" />
								{t("missionControl:addAgent", "Add Agent")}
							</Button>
						</CardContent>
					</Card>
				) : (
					<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
						{agents.map((agent) => (
							<AgentPanel
								key={agent.id}
								agent={agent}
								isSelected={agent.id === selectedAgentId}
								onSelect={() => selectAgent(agent.id)}
								onStart={(task: string) => startAgent(agent.id, task)}
								onPause={() => pauseAgent(agent.id)}
								onResume={() => resumeAgent(agent.id)}
								onStop={() => stopAgent(agent.id)}
								onRemove={() => removeAgent(agent.id)}
								onShowDecisionTree={() => {
									selectAgent(agent.id);
								}}
								onUpdateConfig={(config: Record<string, unknown>) =>
									updateAgentConfig(agent.id, config)
								}
							/>
						))}
					</div>
				)}

				{/* Bottom section: Decision Tree + Event Log */}
				{agents.length > 0 && (
					<div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
						{/* Decision Tree Panel */}
						<Card className="border-border/50">
							<CardHeader className="pb-2">
								<CardTitle className="text-sm font-medium flex items-center gap-2">
									<GitBranch className="h-4 w-4 text-primary" />
									{t("missionControl:decisionTree", "Decision Tree")}
									{selectedAgent && (
										<Badge variant="outline" className="ml-auto text-xs">
											{selectedAgent.name}
										</Badge>
									)}
								</CardTitle>
							</CardHeader>
							<CardContent className="p-3">
								{selectedTree ? (
									<DecisionTreeViewer tree={selectedTree} />
								) : (
									<div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
										{t(
											"missionControl:selectAgentForTree",
											"Select an agent to view its decision tree",
										)}
									</div>
								)}
							</CardContent>
						</Card>

						{/* Event Log */}
						<Card className="border-border/50">
							<CardHeader className="pb-2">
								<CardTitle className="text-sm font-medium flex items-center gap-2">
									<Activity className="h-4 w-4 text-primary" />
									{t("missionControl:eventLog", "Event Log")}
									<Badge variant="outline" className="ml-auto text-xs">
										{events.length}
									</Badge>
								</CardTitle>
							</CardHeader>
							<CardContent className="p-3">
								<AgentEventLog events={events} agents={agents} />
							</CardContent>
						</Card>
					</div>
				)}

				{/* Add Agent Dialog */}
				<AddAgentDialog
					open={showAddAgent}
					onOpenChange={setShowAddAgent}
					onAdd={handleAddAgent}
				/>
			</div>
		</ScrollArea>
	);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatElapsed(seconds: number): string {
	if (seconds < 60) return `${Math.floor(seconds)}s`;
	if (seconds < 3600) {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}m ${s}s`;
	}
	const h = Math.floor(seconds / 3600);
	const m = Math.floor((seconds % 3600) / 60);
	return `${h}h ${m}m`;
}
