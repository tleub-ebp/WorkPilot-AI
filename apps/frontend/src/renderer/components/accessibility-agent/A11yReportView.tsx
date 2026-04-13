import type React from "react";
import type { A11yReport, A11ySeverity } from "../../../shared/types/accessibility";

const SEVERITY_STYLES: Record<A11ySeverity, string> = {
	critical: "text-red-400 bg-red-500/10 border-red-500/20",
	serious: "text-orange-400 bg-orange-500/10 border-orange-500/20",
	moderate: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	minor: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

interface A11yReportViewProps {
	readonly report?: A11yReport;
}

export function A11yReportView({
	report,
}: A11yReportViewProps): React.ReactElement {
	if (!report) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>No accessibility report data available</p>
			</div>
		);
	}
	const criticalCount = report.violations.filter(
		(v) => v.severity === "critical",
	).length;
	const seriousCount = report.violations.filter(
		(v) => v.severity === "serious",
	).length;

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div>
				<h2 className="text-lg font-semibold">Accessibility Report</h2>
				<p className="text-sm text-(--text-secondary)">
					Target: WCAG {report.targetLevel} · {report.filesScanned} files
					scanned
				</p>
			</div>

			<div className="grid grid-cols-4 gap-3">
				<StatCard label="Violations" value={report.violations.length} color="text-red-400" />
				<StatCard label="Critical" value={criticalCount} color="text-red-400" />
				<StatCard label="Serious" value={seriousCount} color="text-orange-400" />
				<StatCard label="Rules Passed" value={report.passedRules.length} color="text-green-400" />
			</div>

			<div className="space-y-2">
				{report.violations.map((v, idx) => (
					<div
						key={`${v.ruleId}-${idx}`}
						className={`px-4 py-3 rounded-lg border ${SEVERITY_STYLES[v.severity]}`}
					>
						<div className="flex items-center gap-2 mb-1">
							<span className="text-xs font-medium uppercase">
								{v.severity}
							</span>
							<span className="text-xs opacity-70">
								{v.ruleId} · {v.wcagCriteria}
							</span>
						</div>
						<p className="text-sm">{v.description}</p>
						<p className="text-xs mt-1 opacity-70 font-mono">
							{v.file}:{v.line}
						</p>
						{v.suggestion && (
							<p className="text-xs mt-1 text-green-400">
								💡 {v.suggestion}
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
	readonly value: number;
	readonly color: string;
}): React.ReactElement {
	return (
		<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
			<p className="text-xs text-(--text-secondary)">{label}</p>
			<p className={`text-2xl font-bold ${color}`}>{value}</p>
		</div>
	);
}
