/**
 * Quality Score Panel Component
 * Displays detailed quality analysis with issues breakdown
 */

import {
	AlertCircle,
	AlertTriangle,
	ChevronDown,
	ChevronRight,
	Info,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type {
	QualityIssue,
	QualityScore,
} from "../../preload/api/modules/quality-api";
import { cn } from "../lib/utils";
import { QualityScoreBadge } from "./QualityScoreBadge";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "./ui/collapsible";

interface QualityScorePanelProps {
	readonly score: QualityScore;
	readonly isLoading?: boolean;
	readonly onRefresh?: () => void;
}

// Icon mapping for severity
const SEVERITY_ICONS: Record<
	string,
	React.ComponentType<{ className?: string }>
> = {
	critical: AlertCircle,
	high: AlertTriangle,
	medium: AlertTriangle,
	low: Info,
};

// Color mapping for severity
const SEVERITY_COLORS: Record<string, string> = {
	critical: "text-red-600 dark:text-red-400",
	high: "text-orange-600 dark:text-orange-400",
	medium: "text-yellow-600 dark:text-yellow-400",
	low: "text-blue-600 dark:text-blue-400",
};

// Category icons
const CATEGORY_ICONS: Record<string, string> = {
	bugs: "ðŸ›",
	security: "ðŸ”’",
	maintainability: "ðŸ”§",
	complexity: "ðŸ“Š",
};

export function QualityScorePanel({
	score,
	isLoading,
	onRefresh,
}: QualityScorePanelProps) {
	const { t } = useTranslation("qualityScore");
	const [isExpanded, setIsExpanded] = useState(true);
	const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
		new Set(),
	);

	const toggleCategory = (category: string) => {
		const newSet = new Set(expandedCategories);
		if (newSet.has(category)) {
			newSet.delete(category);
		} else {
			newSet.add(category);
		}
		setExpandedCategories(newSet);
	};

	// Group issues by category
	const issuesByCategory = score.issues.reduce(
		(acc, issue) => {
			if (!acc[issue.category]) {
				acc[issue.category] = [];
			}
			acc[issue.category].push(issue);
			return acc;
		},
		{} as Record<string, QualityIssue[]>,
	);

	return (
		<Card className="border-l-4 border-l-primary">
			<CardHeader className="pb-3">
				<div className="flex items-center justify-between">
					<CardTitle className="text-lg flex items-center gap-2">
						🧠 {t("title")}
					</CardTitle>
					<QualityScoreBadge
						score={score.overall_score}
						grade={score.grade}
						isPassing={score.is_passing}
					/>
				</div>
			</CardHeader>
			<CardContent className="space-y-4">
				{/* Summary */}
				<div className="flex items-center justify-between text-sm">
					<div className="font-medium">
						{t("score")}: {score.overall_score.toFixed(1)}/100
					</div>
					<div
						className={cn(
							"font-medium",
							score.is_passing
								? "text-green-600 dark:text-green-400"
								: "text-red-600 dark:text-red-400",
						)}
					>
						{score.is_passing ? "✅ " + t("passed") : "❌ " + t("failed")}
					</div>
				</div>

				{/* Issues Summary */}
				{score.total_issues > 0 && (
					<div className="space-y-2">
						<Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
							<CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium w-full hover:underline">
								{isExpanded ? (
									<ChevronDown className="h-4 w-4" />
								) : (
									<ChevronRight className="h-4 w-4" />
								)}
								{t(
									"issuesDetected_" +
										(score.total_issues === 1 ? "one" : "other"),
									{ count: score.total_issues },
								)}
							</CollapsibleTrigger>
							<CollapsibleContent className="mt-3 space-y-2">
								{/* Severity Breakdown */}
								<div className="flex flex-wrap gap-2">
									{score.critical_issues > 0 && (
										<Badge variant="destructive" className="gap-1">
											<AlertCircle className="h-3 w-3" />
											{score.critical_issues} {t("critical")}
										</Badge>
									)}
									{score.issues.some((i) => i.severity === "high") && (
										<Badge
											variant="secondary"
											className="gap-1 bg-orange-100 dark:bg-orange-900/20"
										>
											<AlertTriangle className="h-3 w-3" />
											{score.issues.filter((i) => i.severity === "high").length}{" "}
											{t("high")}
										</Badge>
									)}
									{score.issues.some((i) => i.severity === "medium") && (
										<Badge
											variant="secondary"
											className="gap-1 bg-yellow-100 dark:bg-yellow-900/20"
										>
											<AlertTriangle className="h-3 w-3" />
											{
												score.issues.filter((i) => i.severity === "medium")
													.length
											}{" "}
											{t("medium")}
										</Badge>
									)}
									{score.issues.some((i) => i.severity === "low") && (
										<Badge variant="outline" className="gap-1">
											<Info className="h-3 w-3" />
											{score.issues.filter((i) => i.severity === "low").length}{" "}
											{t("low")}
										</Badge>
									)}
								</div>

								{/* Issues by Category */}
								<div className="mt-4 space-y-3">
									{Object.entries(issuesByCategory).map(
										([category, issues]) => {
											const isOpen = expandedCategories.has(category);
											const icon = CATEGORY_ICONS[category] || "ðŸ“„";

											return (
												<div key={category} className="border rounded-lg p-3">
													<Button
														variant="ghost"
														size="sm"
														className="w-full justify-between h-auto p-0 hover:bg-transparent"
														onClick={() => toggleCategory(category)}
													>
														<div className="flex items-center gap-2">
															{isOpen ? (
																<ChevronDown className="h-4 w-4" />
															) : (
																<ChevronRight className="h-4 w-4" />
															)}
															<span>{icon}</span>
															<span className="font-medium capitalize">
																{t("categories." + category, category)}
															</span>
															<Badge variant="outline" className="ml-2">
																{issues.length}
															</Badge>
														</div>
													</Button>

													{isOpen && (
														<div className="mt-3 space-y-2">
															{issues.slice(0, 5).map((issue) => {
																const SeverityIcon =
																	SEVERITY_ICONS[issue.severity];
																const severityColor =
																	SEVERITY_COLORS[issue.severity];

																// Create a stable key using issue properties
																const issueKey = `${issue.file}-${issue.line || "no-line"}-${issue.title.slice(0, 50)}`;

																return (
																	<div
																		key={issueKey}
																		className="text-sm pl-6 py-2 border-l-2 border-muted"
																	>
																		<div className="flex items-start gap-2">
																			<SeverityIcon
																				className={cn(
																					"h-4 w-4 mt-0.5 flex-shrink-0",
																					severityColor,
																				)}
																			/>
																			<div className="flex-1 min-w-0">
																				<div className="font-medium">
																					{issue.title}
																				</div>
																				<div className="text-xs text-muted-foreground mt-1">
																					{issue.file}
																					{issue.line ? `:${issue.line}` : ""}
																				</div>
																				{issue.suggestion && (
																					<div className="text-xs text-muted-foreground mt-1 flex items-start gap-1">
																						<span>ðŸ’¡</span>
																						<span>{issue.suggestion}</span>
																					</div>
																				)}
																			</div>
																		</div>
																	</div>
																);
															})}
															{issues.length > 5 && (
																<div className="text-xs text-muted-foreground pl-6">
																	{t("andMore", { count: issues.length - 5 })}
																</div>
															)}
														</div>
													)}
												</div>
											);
										},
									)}
								</div>
							</CollapsibleContent>
						</Collapsible>
					</div>
				)}

				{/* No Issues */}
				{score.total_issues === 0 && (
					<div className="text-center py-4 text-muted-foreground">
						<div className="text-4xl mb-2">ðŸŽ‰</div>
						<div className="text-sm">{t("noIssues")}</div>
					</div>
				)}
			</CardContent>
		</Card>
	);
}
