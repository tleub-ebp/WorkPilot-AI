import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupSandboxListeners,
	useSandboxStore,
} from "../../stores/sandbox-store";
import type {
	SimulationResult,
	StepStatus,
} from "../../../shared/types/sandbox";

const STATUS_ICON: Record<StepStatus, string> = {
	success: "✅",
	warning: "⚠️",
	error: "❌",
	skipped: "⏭️",
};

const STATUS_COLORS: Record<StepStatus, string> = {
	success: "text-green-400 bg-green-500/10 border-green-500/20",
	warning: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	error: "text-red-400 bg-red-500/10 border-red-500/20",
	skipped: "text-gray-400 bg-gray-500/10 border-gray-500/20",
};

const CHANGE_COLORS: Record<string, string> = {
	added: "bg-green-500/20 text-green-400",
	modified: "bg-blue-500/20 text-blue-400",
	deleted: "bg-red-500/20 text-red-400",
	renamed: "bg-purple-500/20 text-purple-400",
};

interface SimulationReportProps {
	readonly projectPath?: string;
}

function SummaryCard({
	label,
	value,
	sub,
	color,
}: {
	readonly label: string;
	readonly value: string;
	readonly sub: string;
	readonly color: string;
}): React.ReactElement {
	return (
		<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
			<p className="text-xs text-(--text-secondary)">{label}</p>
			<p className={`text-xl font-bold ${color}`}>{value}</p>
			<p className="text-xs text-(--text-secondary)">{sub}</p>
		</div>
	);
}

function ChangeTypeTag({
	type,
}: {
	readonly type: string;
}): React.ReactElement {
	return (
		<span
			className={`px-1.5 py-0.5 rounded text-xs font-medium ${CHANGE_COLORS[type] ?? ""}`}
		>
			{type.charAt(0).toUpperCase()}
		</span>
	);
}

function ResultBody({
	result,
	t,
}: {
	result: SimulationResult;
	t: (key: string, options?: Record<string, unknown>) => string;
}): React.ReactElement {
	const costSavingPercent =
		result.estimatedRealCostUsd > 0
			? (
					(1 - result.estimatedCostUsd / result.estimatedRealCostUsd) *
					100
				).toFixed(0)
			: "N/A";

	return (
		<div className="flex flex-col gap-4">
			<p className="text-sm text-(--text-secondary)">
				{t("dryRun", { specId: result.specId })}
			</p>

			<div className="grid grid-cols-4 gap-3">
				<SummaryCard
					label={t("steps")}
					value={`${result.successCount}/${result.steps.length}`}
					sub={t("passed")}
					color="text-green-400"
				/>
				<SummaryCard
					label={t("warnings")}
					value={String(result.warningCount)}
					sub={t("issues")}
					color="text-yellow-400"
				/>
				<SummaryCard
					label={t("cost")}
					value={`$${result.estimatedCostUsd.toFixed(4)}`}
					sub={`${costSavingPercent}${t("savedVsReal")}`}
					color="text-blue-400"
				/>
				<SummaryCard
					label={t("files")}
					value={String(result.diffs.length)}
					sub={t("modified")}
					color="text-purple-400"
				/>
			</div>

			{result.steps.length > 0 && (
				<div>
					<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
						{t("executionSteps")}
					</h3>
					<div className="space-y-2">
						{result.steps.map((step) => (
							<div
								key={step.index}
								className={`flex items-center gap-3 px-3 py-2 rounded-lg border ${STATUS_COLORS[step.status]}`}
							>
								<span>{STATUS_ICON[step.status]}</span>
								<span className="flex-1 text-sm">{step.description}</span>
								<span className="text-xs opacity-70">
									{t("durationAndTokens", {
										duration: step.durationMs,
										tokens: step.tokensUsed,
									})}
								</span>
							</div>
						))}
					</div>
				</div>
			)}

			<div>
				<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
					{t("fileChanges")}
				</h3>
				<div className="space-y-1">
					{result.diffs.map((diff) => (
						<div
							key={diff.filePath}
							className="flex items-center gap-3 px-3 py-1.5 text-sm rounded hover:bg-(--bg-secondary)"
						>
							<ChangeTypeTag type={diff.changeType} />
							<span className="flex-1 font-mono text-xs">{diff.filePath}</span>
							<span className="text-green-400 text-xs">+{diff.additions}</span>
							<span className="text-red-400 text-xs">-{diff.deletions}</span>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}

export function SimulationReport({
	projectPath,
}: SimulationReportProps): React.ReactElement {
	const { t } = useTranslation("sandbox");

	useEffect(() => {
		const cleanup = setupSandboxListeners();
		return cleanup;
	}, []);

	const phase = useSandboxStore((s) => s.phase);
	const status = useSandboxStore((s) => s.status);
	const result = useSandboxStore((s) => s.result);
	const error = useSandboxStore((s) => s.error);
	const startScan = useSandboxStore((s) => s.startScan);
	const cancelScan = useSandboxStore((s) => s.cancelScan);
	const reset = useSandboxStore((s) => s.reset);

	const handleRun = (): void => {
		if (!projectPath) return;
		void startScan(projectPath);
	};

	const isScanning = phase === "scanning";

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div className="flex items-center justify-between">
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<div className="flex gap-2">
					{!isScanning && (
						<button
							type="button"
							onClick={handleRun}
							disabled={!projectPath}
							className="px-3 py-1.5 rounded-md bg-blue-500 hover:bg-blue-600 disabled:bg-gray-500 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
						>
							{t("actions.runScan")}
						</button>
					)}
					{isScanning && (
						<button
							type="button"
							onClick={() => void cancelScan()}
							className="px-3 py-1.5 rounded-md bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors"
						>
							{t("actions.cancel")}
						</button>
					)}
					{phase === "complete" && (
						<button
							type="button"
							onClick={reset}
							className="px-3 py-1.5 rounded-md border border-(--border-color) hover:bg-(--bg-secondary) text-sm font-medium transition-colors"
						>
							{t("actions.reset")}
						</button>
					)}
				</div>
			</div>

			{!projectPath && (
				<p className="text-sm text-(--text-secondary)">
					{t("errors.noProject")}
				</p>
			)}

			{isScanning && (
				<p className="text-sm text-(--text-secondary)">
					{status || t("actions.scanning")}
				</p>
			)}

			{phase === "error" && error && (
				<p className="text-sm text-red-400">{t("errors.failed", { error })}</p>
			)}

			{phase === "complete" && result && result.diffs.length === 0 && (
				<p className="text-sm text-(--text-secondary)">{t("noChanges")}</p>
			)}

			{phase === "complete" && result && result.diffs.length > 0 && (
				<ResultBody result={result} t={t} />
			)}
		</div>
	);
}
