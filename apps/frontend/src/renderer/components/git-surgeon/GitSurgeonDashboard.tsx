import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupGitSurgeonListeners,
	useGitSurgeonStore,
} from "../../stores/git-surgeon-store";
import type { SurgeryPlan } from "../../../shared/types/git-surgeon";

interface GitSurgeonDashboardProps {
	readonly projectPath?: string;
}

export function GitSurgeonDashboard({
	projectPath,
}: GitSurgeonDashboardProps): React.ReactElement {
	const { t } = useTranslation("gitSurgeon");

	useEffect(() => {
		const cleanup = setupGitSurgeonListeners();
		return cleanup;
	}, []);

	const phase = useGitSurgeonStore((s) => s.phase);
	const status = useGitSurgeonStore((s) => s.status);
	const plan = useGitSurgeonStore((s) => s.plan);
	const error = useGitSurgeonStore((s) => s.error);
	const startScan = useGitSurgeonStore((s) => s.startScan);
	const cancelScan = useGitSurgeonStore((s) => s.cancelScan);
	const reset = useGitSurgeonStore((s) => s.reset);

	const isScanning = phase === "scanning";
	const canRun = !!projectPath && !isScanning;

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div className="flex items-center gap-3 flex-wrap">
				{isScanning ? (
					<button
						type="button"
						onClick={() => cancelScan()}
						className="px-3 py-1.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-sm hover:bg-red-500/20"
					>
						{t("actions.cancel")}
					</button>
				) : (
					<button
						type="button"
						onClick={() => projectPath && startScan(projectPath)}
						disabled={!canRun}
						className="px-3 py-1.5 rounded bg-(--accent-color) text-white text-sm disabled:opacity-50"
					>
						{t("actions.runScan")}
					</button>
				)}
				{plan && !isScanning && (
					<button
						type="button"
						onClick={reset}
						className="px-3 py-1.5 rounded bg-(--bg-secondary) border border-(--border-color) text-sm hover:bg-(--bg-tertiary)"
					>
						{t("actions.reset")}
					</button>
				)}
			</div>

			{!projectPath && (
				<div className="text-sm text-(--text-secondary)">
					{t("errors.noProject")}
				</div>
			)}

			{isScanning && (
				<div className="text-sm text-(--text-secondary) animate-pulse">
					{status || t("actions.scanning")}
				</div>
			)}

			{phase === "error" && error && (
				<div className="text-sm text-red-400">
					{t("errors.failed", { error })}
				</div>
			)}

			{plan ? (
				<ReportBody plan={plan} t={t} />
			) : (
				phase === "idle" && (
					<div className="flex items-center justify-center h-40 text-(--text-secondary)">
						<p>{t("noData")}</p>
					</div>
				)
			)}
		</div>
	);
}

function ReportBody({
	plan,
	t,
}: {
	readonly plan: SurgeryPlan;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
}): React.ReactElement {
	return (
		<div className="flex flex-col gap-4">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{plan.issues.length} {t("issues")} · ~
					{plan.estimatedSizeSavingsMb.toFixed(1)} MB
				</p>
			</div>

			{plan.requiresForcePush && (
				<div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
					{t("forcePushWarning")}
				</div>
			)}

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
							{issue.filePath && (
								<span className="font-mono">{issue.filePath}</span>
							)}
							{issue.sizeBytes > 0 && (
								<span>{(issue.sizeBytes / 1024 / 1024).toFixed(2)} MB</span>
							)}
						</div>
					</div>
				))}
			</div>

			{plan.actions.length > 0 && (
				<div>
					<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
						{t("plannedActions")}
					</h3>
					<div className="space-y-1">
						{plan.actions.map((action, idx) => (
							<div
								key={`${action.action}-${idx}`}
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
