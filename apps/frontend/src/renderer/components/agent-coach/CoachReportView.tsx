import type React from "react";
import { useTranslation } from "react-i18next";
import type { CoachReport, TipPriority } from "../../../shared/types/agent-coach";

const PRIORITY_STYLES: Record<TipPriority, string> = {
	high: "text-red-400 bg-red-500/10 border-red-500/20",
	medium: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	low: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

interface CoachReportViewProps {
	readonly report?: CoachReport;
}

export function CoachReportView({
	report,
}: CoachReportViewProps): React.ReactElement {
	const { t } = useTranslation("agentCoach");

	if (!report) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>{t("noData")}</p>
			</div>
		);
	}
	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{t("summary", {
						runs: report.totalRuns,
						successRate: (report.successRate * 100).toFixed(1),
						cost: report.totalCostUsd.toFixed(2),
					})}
				</p>
			</div>

			{/* Stats */}
			<div className="grid grid-cols-4 gap-3">
				<StatCard label={t("stats.runs")} value={String(report.totalRuns)} color="text-blue-400" />
				<StatCard
					label={t("stats.successRate")}
					value={`${(report.successRate * 100).toFixed(0)}%`}
					color={report.successRate >= 0.8 ? "text-green-400" : "text-yellow-400"}
				/>
				<StatCard label={t("stats.avgCost")} value={`$${report.avgCostUsd.toFixed(4)}`} color="text-purple-400" />
				<StatCard
					label={t("stats.mostFailing")}
					value={report.mostFailingAgent || t("stats.none")}
					color="text-red-400"
				/>
			</div>

			{/* Tips */}
			<div className="space-y-2">
				{report.tips.map((tip, idx) => (
					<div
						key={`${tip.category}-${idx}`}
						className={`px-4 py-3 rounded-lg border ${PRIORITY_STYLES[tip.priority]}`}
					>
						<div className="flex items-center gap-2 mb-1">
							<span className="text-xs font-medium uppercase">
								{tip.priority}
							</span>
							<span className="text-xs opacity-70">
								{tip.category.replaceAll("_", " ")}
							</span>
						</div>
						<p className="text-sm font-medium">{tip.title}</p>
						<p className="text-xs mt-1 opacity-80">{tip.description}</p>
						{tip.evidence && (
							<p className="text-xs mt-1 opacity-60 italic">
								{t("evidence")} {tip.evidence}
							</p>
						)}
						{tip.action && (
							<p className="text-xs mt-1 text-green-400">
								→ {tip.action}
							</p>
						)}
					</div>
				))}
			</div>

			{report.summary && (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{report.summary}
				</p>
			)}
		</div>
	);
}

function StatCard({
	label,
	value,
	color,
}: {
	readonly label: string;
	readonly value: string;
	readonly color: string;
}): React.ReactElement {
	return (
		<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
			<p className="text-xs text-(--text-secondary)">{label}</p>
			<p className={`text-lg font-bold truncate ${color}`}>{value}</p>
		</div>
	);
}
