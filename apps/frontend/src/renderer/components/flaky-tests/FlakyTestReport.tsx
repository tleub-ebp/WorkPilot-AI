import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupFlakyTestsListeners,
	useFlakyTestsStore,
} from "../../stores/flaky-tests-store";
import type {
	FlakyConfidence,
	FlakyReport,
} from "../../../shared/types/flaky-tests";

const CONFIDENCE_STYLES: Record<FlakyConfidence, string> = {
	high: "text-green-400 bg-green-500/10",
	medium: "text-yellow-400 bg-yellow-500/10",
	low: "text-red-400 bg-red-500/10",
};

interface FlakyTestReportProps {
	readonly projectPath?: string;
}

export function FlakyTestReport({
	projectPath,
}: FlakyTestReportProps): React.ReactElement {
	const { t } = useTranslation("flakyTests");

	useEffect(() => {
		const cleanup = setupFlakyTestsListeners();
		return cleanup;
	}, []);

	const phase = useFlakyTestsStore((s) => s.phase);
	const status = useFlakyTestsStore((s) => s.status);
	const report = useFlakyTestsStore((s) => s.report);
	const error = useFlakyTestsStore((s) => s.error);
	const startScan = useFlakyTestsStore((s) => s.startScan);
	const cancelScan = useFlakyTestsStore((s) => s.cancelScan);
	const reset = useFlakyTestsStore((s) => s.reset);

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
	readonly report: FlakyReport;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
}): React.ReactElement {
	return (
		<div className="flex flex-col gap-4">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{t("summary", {
						flaky: report.flakyCount,
						total: report.totalTests,
					})}
				</p>
			</div>

			<div className="space-y-2">
				{report.flakyTests.map((test) => (
					<div
						key={test.testName}
						className="px-4 py-3 rounded-lg border border-(--border-color) hover:bg-(--bg-secondary) transition-colors"
					>
						<div className="flex items-center justify-between mb-1">
							<p className="text-sm font-medium font-mono">{test.testName}</p>
							<span
								className={`px-2 py-0.5 rounded text-xs font-medium ${CONFIDENCE_STYLES[test.confidence]}`}
							>
								{t("confidence", { level: test.confidence })}
							</span>
						</div>
						<div className="flex items-center gap-4 text-xs text-(--text-secondary)">
							<span>
								{test.failures}/{test.totalRuns} {t("failures")} (
								{(test.flakinessRate * 100).toFixed(1)}%)
							</span>
							<span>
								{t("cause")} {test.probableCause.replaceAll("_", " ")}
							</span>
						</div>
						{test.suggestedFix && (
							<p className="text-xs mt-2 text-green-400">{test.suggestedFix}</p>
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
