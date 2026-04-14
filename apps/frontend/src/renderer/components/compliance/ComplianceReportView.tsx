import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupComplianceListeners,
	useComplianceStore,
} from "../../stores/compliance-store";
import type {
	ComplianceFramework,
	ComplianceReport,
	EvidenceStatus,
} from "../../../shared/types/compliance";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";

const STATUS_STYLES: Record<EvidenceStatus, string> = {
	collected: "text-green-400 bg-green-500/10",
	verified: "text-blue-400 bg-blue-500/10",
	missing: "text-red-400 bg-red-500/10",
	expired: "text-yellow-400 bg-yellow-500/10",
};

const FRAMEWORK_OPTIONS: ComplianceFramework[] = ["SOC2", "ISO_27001"];

interface ComplianceReportViewProps {
	readonly projectPath?: string;
}

export function ComplianceReportView({
	projectPath,
}: ComplianceReportViewProps): React.ReactElement {
	const { t } = useTranslation("compliance");

	useEffect(() => {
		const cleanup = setupComplianceListeners();
		return cleanup;
	}, []);

	const phase = useComplianceStore((s) => s.phase);
	const status = useComplianceStore((s) => s.status);
	const report = useComplianceStore((s) => s.report);
	const error = useComplianceStore((s) => s.error);
	const framework = useComplianceStore((s) => s.framework);
	const setFramework = useComplianceStore((s) => s.setFramework);
	const startScan = useComplianceStore((s) => s.startScan);
	const cancelScan = useComplianceStore((s) => s.cancelScan);
	const reset = useComplianceStore((s) => s.reset);

	const isScanning = phase === "scanning";
	const canRun = !!projectPath && !isScanning;

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div className="flex items-center gap-3 flex-wrap">
				<div className="flex items-center gap-2">
					<span className="text-sm text-(--text-secondary)">
						{t("framework")}
					</span>
					<Select
						value={framework}
						disabled={isScanning}
						onValueChange={(value) => setFramework(value as ComplianceFramework)}
					>
						<SelectTrigger className="w-32">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							{FRAMEWORK_OPTIONS.map((f) => (
								<SelectItem key={f} value={f}>
									{f}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				</div>

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
	readonly report: ComplianceReport;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
}): React.ReactElement {
	let barColor = "bg-red-500";
	if (report.coveragePercent >= 80) {
		barColor = "bg-green-500";
	} else if (report.coveragePercent >= 50) {
		barColor = "bg-yellow-500";
	}

	return (
		<div className="flex flex-col gap-4">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{report.framework} · {report.collectedCount} {t("evidenceItems")} ·{" "}
					{report.coveragePercent}% {t("coverage")}
				</p>
			</div>

			<div className="w-full h-3 rounded-full bg-(--bg-secondary) overflow-hidden">
				<div
					className={`h-full rounded-full transition-all ${barColor}`}
					style={{ width: `${report.coveragePercent}%` }}
				/>
			</div>

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
							<p className="text-sm font-medium truncate">{item.title}</p>
							<p className="text-xs text-(--text-secondary)">
								{item.controlId} · {item.evidenceType.replaceAll("_", " ")}
								{item.source ? ` · ${item.source}` : ""}
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
