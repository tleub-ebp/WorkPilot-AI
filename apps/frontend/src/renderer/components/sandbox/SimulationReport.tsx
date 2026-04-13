import type React from "react";
import type { SimulationResult, StepStatus } from "../../../shared/types/sandbox";

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

interface SimulationReportProps {
	readonly result?: SimulationResult;
	readonly onApprove?: () => void;
	readonly onReject?: () => void;
}

export function SimulationReport({
	result,
	onApprove,
	onReject,
}: SimulationReportProps): React.ReactElement {
	if (!result) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>No simulation data available</p>
			</div>
		);
	}
	const costSavingPercent =
		result.estimatedRealCostUsd > 0
			? (
					(1 - result.estimatedCostUsd / result.estimatedRealCostUsd) *
					100
				).toFixed(0)
			: "N/A";

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-lg font-semibold">
						Sandbox Simulation Report
					</h2>
					<p className="text-sm text-(--text-secondary)">
						Dry-run for spec {result.specId}
					</p>
				</div>
				<div className="flex items-center gap-2">
					{onApprove && (
						<button
							type="button"
							onClick={onApprove}
							className="px-4 py-2 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors text-sm font-medium"
						>
							Approve & Apply
						</button>
					)}
					{onReject && (
						<button
							type="button"
							onClick={onReject}
							className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors text-sm font-medium"
						>
							Reject
						</button>
					)}
				</div>
			</div>

			{/* Summary cards */}
			<div className="grid grid-cols-4 gap-3">
				<SummaryCard
					label="Steps"
					value={`${result.successCount}/${result.steps.length}`}
					sub="passed"
					color="text-green-400"
				/>
				<SummaryCard
					label="Warnings"
					value={String(result.warningCount)}
					sub="issues"
					color="text-yellow-400"
				/>
				<SummaryCard
					label="Cost"
					value={`$${result.estimatedCostUsd.toFixed(4)}`}
					sub={`${costSavingPercent}% saved vs real`}
					color="text-blue-400"
				/>
				<SummaryCard
					label="Files"
					value={String(result.diffs.length)}
					sub="modified"
					color="text-purple-400"
				/>
			</div>

			{/* Steps timeline */}
			<div>
				<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
					Execution Steps
				</h3>
				<div className="space-y-2">
					{result.steps.map((step) => (
						<div
							key={step.index}
							className={`flex items-center gap-3 px-3 py-2 rounded-lg border ${STATUS_COLORS[step.status]}`}
						>
							<span>{STATUS_ICON[step.status]}</span>
							<span className="flex-1 text-sm">
								{step.description}
							</span>
							<span className="text-xs opacity-70">
								{step.durationMs}ms · {step.tokensUsed} tokens
							</span>
						</div>
					))}
				</div>
			</div>

			{/* File changes summary */}
			<div>
				<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
					File Changes
				</h3>
				<div className="space-y-1">
					{result.diffs.map((diff) => (
						<div
							key={diff.filePath}
							className="flex items-center gap-3 px-3 py-1.5 text-sm rounded hover:bg-(--bg-secondary)"
						>
							<ChangeTypeTag type={diff.changeType} />
							<span className="flex-1 font-mono text-xs">
								{diff.filePath}
							</span>
							<span className="text-green-400 text-xs">
								+{diff.additions}
							</span>
							<span className="text-red-400 text-xs">
								-{diff.deletions}
							</span>
						</div>
					))}
				</div>
			</div>
		</div>
	);
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

const CHANGE_COLORS: Record<string, string> = {
	added: "bg-green-500/20 text-green-400",
	modified: "bg-blue-500/20 text-blue-400",
	deleted: "bg-red-500/20 text-red-400",
	renamed: "bg-purple-500/20 text-purple-400",
};

function ChangeTypeTag({
	type,
}: { readonly type: string }): React.ReactElement {
	return (
		<span
			className={`px-1.5 py-0.5 rounded text-xs font-medium ${CHANGE_COLORS[type] ?? ""}`}
		>
			{type.charAt(0).toUpperCase()}
		</span>
	);
}
