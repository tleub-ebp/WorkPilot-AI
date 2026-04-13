import type React from "react";
import { useTranslation } from "react-i18next";
import type { FlakyReport, FlakyConfidence } from "../../../shared/types/flaky-tests";

const CONFIDENCE_STYLES: Record<FlakyConfidence, string> = {
	high: "text-green-400 bg-green-500/10",
	medium: "text-yellow-400 bg-yellow-500/10",
	low: "text-red-400 bg-red-500/10",
};

interface FlakyTestReportProps {
	readonly report?: FlakyReport;
}

export function FlakyTestReport({
	report,
}: FlakyTestReportProps): React.ReactElement {
	const { t } = useTranslation("flakyTests");

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
							<p className="text-sm font-medium font-mono">
								{test.testName}
							</p>
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
							<p className="text-xs mt-2 text-green-400">
								💡 {test.suggestedFix}
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
