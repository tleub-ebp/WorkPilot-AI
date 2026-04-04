import {
	Activity,
	ChevronDown,
	Clock,
	Coins,
	Eye,
	GitPullRequest,
	Info,
	MessageSquare,
	Moon,
	Shield,
	Zap,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { useCurrency } from "../../hooks/useCurrency";
import { useContinuousAIStore } from "../../stores/continuous-ai-store";
import { Label } from "../ui/label";
import { Switch } from "../ui/switch";
import { SettingsSection } from "./SettingsSection";

// Type alias for module keys to avoid union type repetition
type ModuleKey =
	| "cicd_watcher"
	| "dependency_sentinel"
	| "issue_responder"
	| "pr_reviewer";

/**
 * Continuous AI settings panel.
 *
 * Master toggle + per-module configuration for the always-on background daemon.
 * Works with any LLM configured in the user's active profile.
 */
export function ContinuousAISettings() {
	const { t } = useTranslation(["continuousAI", "common"]);
	const { config, setConfig, setModuleConfig } = useContinuousAIStore();
	const { format, convert, toUsd } = useCurrency();
	const [expandedModule, setExpandedModule] = useState<string | null>(null);

	const toggleModule = (key: string) => {
		setExpandedModule(expandedModule === key ? null : key);
	};

	const modules = [
		{
			key: "cicd_watcher",
			configKey: "cicdWatcher" as const,
			icon: Eye,
			color: "text-blue-500",
			bgColor: "bg-blue-500/10",
		},
		{
			key: "dependency_sentinel",
			configKey: "dependencySentinel" as const,
			icon: Shield,
			color: "text-green-500",
			bgColor: "bg-green-500/10",
		},
		{
			key: "issue_responder",
			configKey: "issueResponder" as const,
			icon: MessageSquare,
			color: "text-amber-500",
			bgColor: "bg-amber-500/10",
		},
		{
			key: "pr_reviewer",
			configKey: "prReviewer" as const,
			icon: GitPullRequest,
			color: "text-purple-500",
			bgColor: "bg-purple-500/10",
		},
	] as const;

	return (
		<SettingsSection
			title={t("continuousAI:title")}
			description={t("continuousAI:subtitle")}
		>
			<div className="space-y-6">
				{/* ── Master Toggle ──────────────────────────────── */}
				<div className="flex items-center justify-between rounded-lg border border-border p-4">
					<div className="flex items-center gap-3">
						<div
							className={cn(
								"flex h-10 w-10 items-center justify-center rounded-lg",
								config.enabled
									? "bg-primary/10 text-primary"
									: "bg-muted text-muted-foreground",
							)}
						>
							<Activity className="h-5 w-5" />
						</div>
						<div>
							<Label className="text-sm font-medium">
								{t("continuousAI:enable")}
							</Label>
							<p className="text-xs text-muted-foreground mt-0.5">
								{t("continuousAI:subtitle")}
							</p>
						</div>
					</div>
					<Switch
						checked={config.enabled}
						onCheckedChange={(v) => setConfig({ enabled: v })}
					/>
				</div>

				{/* ── Info Banner ────────────────────────────────── */}
				{config.enabled && (
					<div className="flex items-start gap-2.5 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
						<Info className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
						<p className="text-xs text-blue-600 dark:text-blue-400 leading-relaxed">
							{t("continuousAI:infoBanner")}
						</p>
					</div>
				)}

				{config.enabled && (
					<div className="space-y-5">
						{/* ── Daily Budget ──────────────────────────────── */}
						<div className="space-y-2.5 rounded-lg border border-border p-4">
							<div className="flex items-center justify-between">
								<Label className="text-sm font-medium flex items-center gap-2">
									<Coins className="h-3.5 w-3.5 text-primary" />
									{t("continuousAI:budget.title")}
								</Label>
								<span className="text-sm font-mono tabular-nums bg-muted px-2 py-0.5 rounded">
									{format(config.dailyBudgetUsd)}
								</span>
							</div>
							<input
								type="range"
								min={1}
								max={50}
								step={1}
								value={Math.round(convert(config.dailyBudgetUsd))}
								onChange={(e) =>
									setConfig({
										dailyBudgetUsd: toUsd(Number.parseInt(e.target.value, 10)),
									})
								}
								className="w-full accent-primary"
							/>
							<div className="flex justify-between text-[10px] text-muted-foreground px-0.5">
								<span>{format(1)}</span>
								<span>{format(10)}</span>
								<span>{format(25)}</span>
								<span>{format(50)}</span>
							</div>
						</div>

						{/* ── Modules ───────────────────────────────────── */}
						<div className="space-y-3">
							<Label className="text-sm font-medium flex items-center gap-2 px-1">
								<Zap className="h-3.5 w-3.5 text-primary" />
								{t("continuousAI:modules.title")}
							</Label>

							{modules.map((mod) => {
								const Icon = mod.icon;
								const moduleConfig = config[mod.configKey];
								const isExpanded = expandedModule === mod.key;

								return (
									<div
										key={mod.key}
										className={cn(
											"rounded-lg border transition-colors",
											moduleConfig.enabled
												? "border-primary/30 bg-primary/2"
												: "border-border",
										)}
									>
										{/* Module Header */}
										<div className="flex items-center justify-between p-3">
											<button
												type="button"
												onClick={() => toggleModule(mod.key)}
												className="flex items-center gap-3 flex-1 text-left"
											>
												<div
													className={cn(
														"flex h-8 w-8 items-center justify-center rounded-md",
														moduleConfig.enabled ? mod.bgColor : "bg-muted",
													)}
												>
													<Icon
														className={cn(
															"h-4 w-4",
															moduleConfig.enabled
																? mod.color
																: "text-muted-foreground",
														)}
													/>
												</div>
												<div className="min-w-0 flex-1">
													<div className="text-sm font-medium">
														{t(`continuousAI:modules.${mod.configKey}.title`)}
													</div>
													<div className="text-xs text-muted-foreground truncate">
														{t(
															`continuousAI:modules.${mod.configKey}.description`,
														)}
													</div>
												</div>
												<ChevronDown
													className={cn(
														"h-4 w-4 text-muted-foreground transition-transform mr-3",
														isExpanded && "rotate-180",
													)}
												/>
											</button>
											<Switch
												checked={moduleConfig.enabled}
												onCheckedChange={(v) =>
													setModuleConfig(mod.key, { enabled: v })
												}
											/>
										</div>

										{/* Module Details */}
										{isExpanded && moduleConfig.enabled && (
											<div className="px-4 pb-4 pt-1 space-y-4 border-t border-border/50">
												{/* Common settings */}
												<div className="grid grid-cols-2 gap-4">
													{/* Poll Interval */}
													<div className="space-y-1.5">
														<Label className="text-xs flex items-center gap-1.5">
															<Clock className="h-3 w-3" />
															{t("continuousAI:config.pollInterval")}
														</Label>
														<select
															value={moduleConfig.pollIntervalSeconds}
															onChange={(e) =>
																setModuleConfig(mod.key, {
																	pollIntervalSeconds: Number.parseInt(
																		e.target.value,
																		10,
																	),
																})
															}
															className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs"
														>
															<option value={60}>1 min</option>
															<option value={180}>3 min</option>
															<option value={300}>5 min</option>
															<option value={600}>10 min</option>
															<option value={1800}>30 min</option>
															<option value={3600}>1 h</option>
															<option value={86400}>24 h</option>
														</select>
													</div>

													{/* Max Actions / Hour */}
													<div className="space-y-1.5">
														<Label className="text-xs">
															{t("continuousAI:config.maxActionsPerHour")}
														</Label>
														<input
															type="number"
															min={1}
															max={50}
															value={moduleConfig.maxActionsPerHour}
															onChange={(e) =>
																setModuleConfig(mod.key, {
																	maxActionsPerHour:
																		Number.parseInt(e.target.value, 10) || 1,
																})
															}
															className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs font-mono"
														/>
													</div>
												</div>

												{/* Auto Act */}
												<div className="flex items-center justify-between">
													<Label className="text-xs flex items-center gap-1.5">
														<Zap className="h-3 w-3" />
														{t("continuousAI:config.autoAct")}
													</Label>
													<Switch
														checked={moduleConfig.autoAct}
														onCheckedChange={(v) =>
															setModuleConfig(mod.key, { autoAct: v })
														}
													/>
												</div>

												{/* Quiet Hours */}
												<div className="space-y-1.5">
													<Label className="text-xs flex items-center gap-1.5">
														<Moon className="h-3 w-3" />
														{t("continuousAI:config.quietHours")}
													</Label>
													<div className="flex items-center gap-2">
														<input
															type="time"
															value={moduleConfig.quietHoursStart}
															onChange={(e) =>
																setModuleConfig(mod.key, {
																	quietHoursStart: e.target.value,
																})
															}
															className="rounded-md border border-input bg-background px-2 py-1 text-xs"
														/>
														<span className="text-xs text-muted-foreground">
															→
														</span>
														<input
															type="time"
															value={moduleConfig.quietHoursEnd}
															onChange={(e) =>
																setModuleConfig(mod.key, {
																	quietHoursEnd: e.target.value,
																})
															}
															className="rounded-md border border-input bg-background px-2 py-1 text-xs"
														/>
													</div>
												</div>

												{/* ── Module-specific options ─── */}
												<div className="border-t border-border/50 pt-3 space-y-3">
													{mod.key === "cicd_watcher" && (
														<>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.cicdWatcher.autoFix",
																	)}
																</Label>
																<Switch
																	checked={config.cicdWatcher.autoFix}
																	onCheckedChange={(v) =>
																		setModuleConfig("cicd_watcher", {
																			autoFix: v,
																		})
																	}
																/>
															</div>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.cicdWatcher.autoCreatePr",
																	)}
																</Label>
																<Switch
																	checked={config.cicdWatcher.autoCreatePr}
																	onCheckedChange={(v) =>
																		setModuleConfig("cicd_watcher", {
																			autoCreatePr: v,
																		})
																	}
																/>
															</div>
														</>
													)}

													{mod.key === "dependency_sentinel" && (
														<>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.dependencySentinel.autoPatchMinor",
																	)}
																</Label>
																<Switch
																	checked={
																		config.dependencySentinel.autoPatchMinor
																	}
																	onCheckedChange={(v) =>
																		setModuleConfig("dependency_sentinel", {
																			autoPatchMinor: v,
																		})
																	}
																/>
															</div>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.dependencySentinel.autoPatchMajor",
																	)}
																</Label>
																<Switch
																	checked={
																		config.dependencySentinel.autoPatchMajor
																	}
																	onCheckedChange={(v) =>
																		setModuleConfig("dependency_sentinel", {
																			autoPatchMajor: v,
																		})
																	}
																/>
															</div>
														</>
													)}

													{mod.key === "issue_responder" && (
														<>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.issueResponder.autoTriage",
																	)}
																</Label>
																<Switch
																	checked={config.issueResponder.autoTriage}
																	onCheckedChange={(v) =>
																		setModuleConfig("issue_responder", {
																			autoTriage: v,
																		})
																	}
																/>
															</div>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.issueResponder.autoInvestigate",
																	)}
																</Label>
																<Switch
																	checked={
																		config.issueResponder.autoInvestigateBugs
																	}
																	onCheckedChange={(v) =>
																		setModuleConfig("issue_responder", {
																			autoInvestigateBugs: v,
																		})
																	}
																/>
															</div>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.issueResponder.autoCreateSpecs",
																	)}
																</Label>
																<Switch
																	checked={
																		config.issueResponder.autoCreateSpecs
																	}
																	onCheckedChange={(v) =>
																		setModuleConfig("issue_responder", {
																			autoCreateSpecs: v,
																		})
																	}
																/>
															</div>
														</>
													)}

													{mod.key === "pr_reviewer" && (
														<>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.prReviewer.autoApproveTrivial",
																	)}
																</Label>
																<Switch
																	checked={config.prReviewer.autoApproveTrivial}
																	onCheckedChange={(v) =>
																		setModuleConfig("pr_reviewer", {
																			autoApproveTrivial: v,
																		})
																	}
																/>
															</div>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.prReviewer.reviewExternalOnly",
																	)}
																</Label>
																<Switch
																	checked={config.prReviewer.reviewExternalOnly}
																	onCheckedChange={(v) =>
																		setModuleConfig("pr_reviewer", {
																			reviewExternalOnly: v,
																		})
																	}
																/>
															</div>
															<div className="flex items-center justify-between">
																<Label className="text-xs">
																	{t(
																		"continuousAI:modules.prReviewer.postComments",
																	)}
																</Label>
																<Switch
																	checked={config.prReviewer.postReviewComments}
																	onCheckedChange={(v) =>
																		setModuleConfig("pr_reviewer", {
																			postReviewComments: v,
																		})
																	}
																/>
															</div>
														</>
													)}
												</div>
											</div>
										)}
									</div>
								);
							})}
						</div>
					</div>
				)}
			</div>
		</SettingsSection>
	);
}
