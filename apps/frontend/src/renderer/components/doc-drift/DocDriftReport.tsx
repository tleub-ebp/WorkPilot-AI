import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupDocDriftListeners,
	useDocDriftStore,
} from "../../stores/doc-drift-store";
import type { DriftReport, DriftSeverity } from "../../../shared/types/doc-drift";

const SEVERITY_STYLES: Record<DriftSeverity, string> = {
	high: "text-red-400 bg-red-500/10 border-red-500/20",
	medium: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	low: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

interface DocDriftReportProps {
	readonly projectPath?: string;
}

export function DocDriftReport({
	projectPath,
}: DocDriftReportProps): React.ReactElement {
	const { t } = useTranslation("docDrift");

	useEffect(() => {
		const cleanup = setupDocDriftListeners();
		return cleanup;
	}, []);

	const phase = useDocDriftStore((s) => s.phase);
	const status = useDocDriftStore((s) => s.status);
	const report = useDocDriftStore((s) => s.report);
	const error = useDocDriftStore((s) => s.error);
	const startScan = useDocDriftStore((s) => s.startScan);
	const cancelScan = useDocDriftStore((s) => s.cancelScan);
	const reset = useDocDriftStore((s) => s.reset);

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
				{report && !isScanning && (
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

			{report ? (
				<ReportBody report={report} t={t} />
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
	report,
	t,
}: {
	readonly report: DriftReport;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
}): React.ReactElement {
	return (
		<div className="flex flex-col gap-4">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{t("info", {
						docs: report.docsScanned,
						files: report.codeFilesIndexed,
					})}
				</p>
			</div>

			<div className="space-y-2">
				{report.issues.map((issue) => (
					<div
						key={`${issue.docFile}-${issue.docLine}-${issue.severity}`}
						className={`px-4 py-3 rounded-lg border ${SEVERITY_STYLES[issue.severity]}`}
					>
						<div className="flex items-center gap-2 mb-1">
							<span className="text-xs font-medium uppercase">
								{t(issue.severity)}
							</span>
							<span className="text-xs opacity-70">
								{issue.driftType.replaceAll("_", " ")}
							</span>
						</div>
						<p className="text-sm">{issue.message}</p>
						<p className="text-xs mt-1 opacity-70 font-mono">
							{issue.docFile}:{issue.docLine} → {issue.referencedSymbol}
						</p>
						{issue.suggestion && (
							<p className="text-xs mt-1 text-green-400">{issue.suggestion}</p>
						)}
					</div>
				))}
			</div>

			{report.issues.length === 0 ? (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{t("noDriftDetected")}
				</p>
			) : (
				report.summary && (
					<p className="text-sm text-(--text-secondary) italic mt-2">
						{report.summary}
					</p>
				)
			)}
		</div>
	);
}
