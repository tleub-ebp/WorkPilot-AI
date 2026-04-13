import type React from "react";
import { useTranslation } from "react-i18next";
import type {
	ComplianceReport,
	EvidenceStatus,
} from "../../../shared/types/compliance";

const STATUS_STYLES: Record<EvidenceStatus, string> = {
	collected: "text-green-400 bg-green-500/10",
	verified: "text-blue-400 bg-blue-500/10",
	missing: "text-red-400 bg-red-500/10",
	expired: "text-yellow-400 bg-yellow-500/10",
};

interface ComplianceReportViewProps {
	readonly report?: ComplianceReport;
}

export function ComplianceReportView({
	report,
}: ComplianceReportViewProps): React.ReactElement {
	const { t } = useTranslation("compliance");
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
					{report.framework} · {report.collectedCount} {t("evidenceItems")} ·{" "}
					{report.coveragePercent}% {t("coverage")}
				</p>
			</div>

			{/* Coverage bar */}
			<div className="w-full h-3 rounded-full bg-(--bg-secondary) overflow-hidden">
				<div
					className={`h-full rounded-full transition-all ${(() => {
						if (report.coveragePercent >= 80) {
							return "bg-green-500";
						}
						if (report.coveragePercent >= 50) {
							return "bg-yellow-500";
						}
						return "bg-red-500";
					})()}`}
					style={{ width: `${report.coveragePercent}%` }}
				/>
			</div>

			{/* Missing controls */}
			{report.missingControls.length > 0 && (
				<div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
					<p className="text-xs font-medium text-red-400 mb-1">
						{t("missingControls")}
					</p>
					<div className="flex flex-wrap gap-1">
						{report.missingControls.map((ctrl) => (
							<span
								key={ctrl}
								className="px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-300"
							>
								{ctrl}
							</span>
						))}
					</div>
				</div>
			)}

			{/* Evidence table */}
			<div className="space-y-2">
				{report.evidence.map((item) => (
					<div
						key={item.id}
						className="flex items-center gap-3 px-4 py-3 rounded-lg border border-(--border-color) hover:bg-(--bg-secondary) transition-colors"
					>
						<span
							className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLES[item.status]}`}
						>
							{item.status}
						</span>
						<div className="flex-1 min-w-0">
							<p className="text-sm font-medium truncate">
								{item.title}
							</p>
							<p className="text-xs text-(--text-secondary)">
								{item.controlId} · {item.evidenceType.replaceAll("_", " ")}
							</p>
						</div>
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
