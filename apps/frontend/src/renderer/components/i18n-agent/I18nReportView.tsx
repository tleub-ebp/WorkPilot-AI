import type React from "react";
import { useTranslation } from "react-i18next";
import type { I18nReport, I18nSeverity } from "../../../shared/types/i18n-agent";

const SEVERITY_STYLES: Record<I18nSeverity, string> = {
	error: "text-red-400 bg-red-500/10 border-red-500/20",
	warning: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	info: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

interface I18nReportViewProps {
	readonly report?: I18nReport;
}

export function I18nReportView({
	report,
}: I18nReportViewProps): React.ReactElement {
	const { t } = useTranslation("i18nAgent");

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
					{t("filesInfo", {
						count: report.filesScanned,
						locales: report.localesCompared.join(", "),
					})}
				</p>
			</div>

			{/* Coverage by locale */}
			<div className="grid grid-cols-4 gap-3">
				{Object.entries(report.coverageByLocale).map(([locale, pct]) => {
					let coverageColor: string;
					if (pct >= 90) {
						coverageColor = "text-green-400";
					} else if (pct >= 70) {
						coverageColor = "text-yellow-400";
					} else {
						coverageColor = "text-red-400";
					}
					return (
						<div
							key={locale}
							className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)"
						>
							<p className="text-xs text-(--text-secondary)">
								{t("locale")}: {locale}
							</p>
							<p className={`text-xl font-bold ${coverageColor}`}>
								{pct}%
							</p>
						</div>
					);
				})}
			</div>

			{/* Issues */}
			<div className="space-y-2">
				{report.issues.map((issue, idx) => (
					<div
						key={`${issue.key}-${idx}`}
						className={`px-4 py-3 rounded-lg border ${SEVERITY_STYLES[issue.severity]}`}
					>
						<div className="flex items-center gap-2 mb-1">
							<span className="text-xs font-medium uppercase">
								{issue.severity}
							</span>
							<span className="text-xs opacity-70">
								{issue.issueType.replaceAll("_", " ")}
							</span>
						</div>
						<p className="text-sm">{issue.message}</p>
						<p className="text-xs mt-1 opacity-70 font-mono">
							{issue.file}:{issue.line} · locale: {issue.locale}
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
