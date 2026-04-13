import type React from "react";
import { useTranslation } from "react-i18next";
import type { DriftReport, DriftSeverity } from "../../../shared/types/doc-drift";

const SEVERITY_STYLES: Record<DriftSeverity, string> = {
	high: "text-red-400 bg-red-500/10 border-red-500/20",
	medium: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	low: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

interface DocDriftReportProps {
	readonly report?: DriftReport;
}

export function DocDriftReport({
	report,
}: DocDriftReportProps): React.ReactElement {
	const { t } = useTranslation("docDrift");
	if (!report) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>{t("noDataAvailable")}</p>
			</div>
		);
	}
	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{report.docsScanned} docs scanned · {report.codeFilesIndexed} code
					files indexed
				</p>
			</div>

			<div className="space-y-2">
				{report.issues.map((issue, idx) => (
					<div
						key={`${issue.docFile}-${idx}`}
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
							<p className="text-xs mt-1 text-green-400">
								💡 {issue.suggestion}
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
