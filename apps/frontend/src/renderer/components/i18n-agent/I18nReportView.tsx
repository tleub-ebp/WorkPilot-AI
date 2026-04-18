import type React from "react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
	setupI18nAgentListeners,
	useI18nAgentStore,
} from "../../stores/i18n-agent-store";
import type {
	I18nReport,
	I18nSeverity,
} from "../../../shared/types/i18n-agent";

const SEVERITY_STYLES: Record<I18nSeverity, string> = {
	error: "text-red-400 bg-red-500/10 border-red-500/20",
	warning: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	info: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

interface I18nReportViewProps {
	readonly projectPath?: string;
}

export function I18nReportView({
	projectPath,
}: I18nReportViewProps): React.ReactElement {
	const { t } = useTranslation("i18nAgent");

	useEffect(() => {
		const cleanup = setupI18nAgentListeners();
		return cleanup;
	}, []);

	const phase = useI18nAgentStore((s) => s.phase);
	const status = useI18nAgentStore((s) => s.status);
	const report = useI18nAgentStore((s) => s.report);
	const error = useI18nAgentStore((s) => s.error);
	const startScan = useI18nAgentStore((s) => s.startScan);
	const cancelScan = useI18nAgentStore((s) => s.cancelScan);
	const reset = useI18nAgentStore((s) => s.reset);
	const [searchQuery, setSearchQuery] = useState("");

	const isScanning = phase === "scanning";
	const canRun = !!projectPath && !isScanning;

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<Toolbar
				canRun={canRun}
				isScanning={isScanning}
				hasReport={!!report}
				onRun={() => projectPath && startScan(projectPath)}
				onCancel={() => cancelScan()}
				onReset={reset}
				t={t}
			/>

			{report && !isScanning && (
				<input
					type="text"
					value={searchQuery}
					onChange={(e) => setSearchQuery(e.target.value)}
					placeholder={t("search.placeholder")}
					className="px-3 py-2 rounded bg-(--bg-secondary) border border-(--border-color) text-(--text-primary) text-sm focus:outline-none focus:ring-2 focus:ring-(--accent-color)"
				/>
			)}

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
				<ReportBody report={report} t={t} searchQuery={searchQuery} />
			) : (
				phase === "idle" && (
					<div className="flex flex-col items-center justify-center h-40 text-(--text-secondary)">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							strokeWidth={1.5}
							stroke="currentColor"
							className="w-16 h-16 mb-4 opacity-50"
						>
							<title>Global network icon</title>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418"
							/>
						</svg>
						<p className="text-center">{t("noData")}</p>
					</div>
				)
			)}
		</div>
	);
}

function Toolbar({
	canRun,
	isScanning,
	hasReport,
	onRun,
	onCancel,
	onReset,
	t,
}: {
	readonly canRun: boolean;
	readonly isScanning: boolean;
	readonly hasReport: boolean;
	readonly onRun: () => void;
	readonly onCancel: () => void;
	readonly onReset: () => void;
	readonly t: (key: string) => string;
}): React.ReactElement {
	return (
		<div className="flex items-center gap-3 flex-wrap">
			{isScanning ? (
				<button
					type="button"
					onClick={onCancel}
					className="px-3 py-1.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-sm hover:bg-red-500/20"
				>
					{t("actions.cancel")}
				</button>
			) : (
				<button
					type="button"
					onClick={onRun}
					disabled={!canRun}
					className="px-3 py-1.5 rounded bg-(--accent-color) text-white text-sm disabled:opacity-50"
				>
					{t("actions.runScan")}
				</button>
			)}

			{hasReport && !isScanning && (
				<button
					type="button"
					onClick={onReset}
					className="px-3 py-1.5 rounded bg-(--bg-secondary) border border-(--border-color) text-sm hover:bg-(--bg-tertiary)"
				>
					{t("actions.reset")}
				</button>
			)}
		</div>
	);
}

function ReportBody({
	report,
	t,
	searchQuery,
}: {
	readonly report: I18nReport;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
	readonly searchQuery: string;
}): React.ReactElement {
	const filteredIssues = searchQuery
		? report.issues.filter(
				(issue) =>
					issue.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
					issue.file.toLowerCase().includes(searchQuery.toLowerCase()) ||
					issue.issueType.toLowerCase().includes(searchQuery.toLowerCase()) ||
					(issue.locale?.toLowerCase().includes(searchQuery.toLowerCase())),
			)
		: report.issues;

	return (
		<div className="flex flex-col gap-4">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{t("filesInfo", {
						count: report.filesScanned,
						locales: report.localesCompared.join(", ") || "—",
					})}
				</p>
			</div>

			{Object.keys(report.coverageByLocale).length > 0 && (
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
								<p className={`text-xl font-bold ${coverageColor}`}>{pct}%</p>
							</div>
						);
					})}
				</div>
			)}

			<div className="space-y-2">
				{filteredIssues.length === 0 && searchQuery ? (
					<div className="text-sm text-(--text-secondary) text-center py-4">
						{t("search.noResults")}
					</div>
				) : (
					filteredIssues.map((issue) => (
						<div
							key={`${issue.file}-${issue.line}-${issue.key}`}
							className={`px-4 py-3 rounded-lg border ${SEVERITY_STYLES[issue.severity]}`}
						>
							<div className="flex items-center gap-2 mb-1">
								<span className="text-xs font-medium uppercase">
									{t(`severity.${issue.severity}`)}
								</span>
								<span className="text-xs opacity-70">
									{t(`issueType.${issue.issueType}`)}
								</span>
							</div>
							<p className="text-sm">{issue.message}</p>
							<p className="text-xs mt-1 opacity-70 font-mono">
								{issue.file}
								{issue.line ? `:${issue.line}` : ""}
								{issue.locale ? ` · ${t("localeLabel")}: ${issue.locale}` : ""}
							</p>
							{issue.suggestion && (
								<p className="text-xs mt-1 text-green-400">{issue.suggestion}</p>
							)}
						</div>
					))
				)}
			</div>

			{report.summary && (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{report.summary}
				</p>
			)}
		</div>
	);
}
