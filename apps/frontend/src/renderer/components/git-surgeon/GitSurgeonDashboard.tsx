import type React from "react";
import { useTranslation } from "react-i18next";
import type { SurgeryPlan } from "../../../shared/types/git-surgeon";

interface GitSurgeonDashboardProps {
	readonly plan?: SurgeryPlan;
	readonly onExecute?: () => void;
}

export function GitSurgeonDashboard({
	plan,
	onExecute,
}: GitSurgeonDashboardProps): React.ReactElement {
	const { t } = useTranslation("gitSurgeon");
	if (!plan) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>{t("noDataAvailable")}</p>
			</div>
		);
	}
	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-lg font-semibold">{t("title")}</h2>
					<p className="text-sm text-(--text-secondary)">
						{plan.issues.length} {t("issues")} · ~
						{plan.estimatedSizeSavingsMb.toFixed(1)} {t("potentialSavings", { mb: plan.estimatedSizeSavingsMb.toFixed(1) })}
					</p>
				</div>
				{onExecute && (
					<button
						type="button"
						onClick={onExecute}
						className="px-4 py-2 rounded-lg bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 transition-colors text-sm font-medium"
					>
						{t("executeSurgery")}
					</button>
				)}
			</div>

			{plan.requiresForcePush && (
				<div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
					{t("forcePushWarning")}
				</div>
			)}

			{/* Issues */}
			<div className="space-y-2">
				{plan.issues.map((issue, idx) => (
					<div
						key={`${issue.commitSha}-${idx}`}
						className="px-4 py-3 rounded-lg border border-(--border-color) hover:bg-(--bg-secondary) transition-colors"
					>
						<div className="flex items-center gap-2 mb-1">
							<span className="text-xs font-medium uppercase text-yellow-400">
								{issue.severity}
							</span>
							<span className="text-xs opacity-70">
								{issue.issueType.replaceAll("_", " ")}
							</span>
						</div>
						<p className="text-sm">{issue.description}</p>
						<div className="flex items-center gap-4 text-xs text-(--text-secondary) mt-1">
							<span className="font-mono">{issue.commitSha.slice(0, 8)}</span>
							{issue.filePath && <span className="font-mono">{issue.filePath}</span>}
							{issue.sizeBytes > 0 && (
								<span>{(issue.sizeBytes / 1024 / 1024).toFixed(2)} MB</span>
							)}
						</div>
					</div>
				))}
			</div>

			{/* Planned actions */}
			{plan.actions.length > 0 && (
				<div>
					<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
						{t("plannedActions")}
					</h3>
					<div className="space-y-1">
						{plan.actions.map((action) => (
							<div
								key={action.action}
								className="flex items-center gap-2 px-3 py-2 rounded text-sm bg-(--bg-secondary)"
							>
								<span className="text-purple-400 font-mono text-xs">
									{action.action}
								</span>
								<span>{action.description}</span>
							</div>
						))}
					</div>
				</div>
			)}

			{plan.summary && (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{plan.summary}
				</p>
			)}
		</div>
	);
}
