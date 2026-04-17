import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupCarbonProfilerListeners,
	useCarbonProfilerStore,
} from "../../stores/carbon-profiler-store";
import type { CarbonReport } from "../../../shared/types/carbon-profiler";

interface CarbonReportViewProps {
	readonly projectPath?: string;
}

export function CarbonReportView({
	projectPath,
}: CarbonReportViewProps): React.ReactElement {
	const { t } = useTranslation("carbonProfiler");

	useEffect(() => {
		const cleanup = setupCarbonProfilerListeners();
		return cleanup;
	}, []);

	const phase = useCarbonProfilerStore((s) => s.phase);
	const status = useCarbonProfilerStore((s) => s.status);
	const report = useCarbonProfilerStore((s) => s.report);
	const error = useCarbonProfilerStore((s) => s.error);
	const startScan = useCarbonProfilerStore((s) => s.startScan);
	const cancelScan = useCarbonProfilerStore((s) => s.cancelScan);
	const reset = useCarbonProfilerStore((s) => s.reset);

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

function StatCard({
	label,
	value,
	color,
}: {
	readonly label: string;
	readonly value: string;
	readonly color: string;
}): React.ReactElement {
	return (
		<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
			<p className="text-xs text-(--text-secondary)">{label}</p>
			<p className={`text-xl font-bold ${color}`}>{value}</p>
		</div>
	);
}

function ReportBody({
	report,
	t,
}: {
	readonly report: CarbonReport;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
}): React.ReactElement {
	return (
		<div className="flex flex-col gap-4">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{report.periodStart || "—"} → {report.periodEnd || "—"}
				</p>
			</div>

			<div className="grid grid-cols-3 gap-3">
				<StatCard
					label={t("totalEnergy")}
					value={`${report.totalKwh.toFixed(3)} kWh`}
					color="text-yellow-400"
				/>
				<StatCard
					label={t("co2Emissions")}
					value={`${report.totalCo2G.toFixed(1)} g`}
					color="text-red-400"
				/>
				<StatCard
					label={t("records")}
					value={String(report.records.length)}
					color="text-blue-400"
				/>
			</div>

			{Object.keys(report.byProvider).length > 0 && (
				<div>
					<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
						{t("co2ByProvider")}
					</h3>
					<div className="grid grid-cols-4 gap-2">
						{Object.entries(report.byProvider).map(([provider, co2]) => (
							<div
								key={provider}
								className="p-2 rounded-lg bg-(--bg-secondary) border border-(--border-color)"
							>
								<p className="text-xs text-(--text-secondary) truncate">
									{provider}
								</p>
								<p className="text-sm font-bold text-orange-400">
									{co2.toFixed(1)}
								</p>
							</div>
						))}
					</div>
				</div>
			)}

			{Object.keys(report.byModel).length > 0 && (
				<div>
					<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
						{t("co2ByModel")}
					</h3>
					<div className="grid grid-cols-4 gap-2">
						{Object.entries(report.byModel).map(([model, co2]) => (
							<div
								key={model}
								className="p-2 rounded-lg bg-(--bg-secondary) border border-(--border-color)"
							>
								<p className="text-xs text-(--text-secondary) truncate">
									{model}
								</p>
								<p className="text-sm font-bold text-purple-400">
									{co2.toFixed(1)}
								</p>
							</div>
						))}
					</div>
				</div>
			)}

			{report.records.length > 0 && (
				<div>
					<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
						{t("recentRecords")}
					</h3>
					<div className="space-y-1">
						{report.records.slice(0, 20).map((rec) => (
							<div
								key={rec.timestamp}
								className="flex items-center gap-3 px-3 py-2 text-xs rounded hover:bg-(--bg-secondary) transition-colors"
							>
								<span className="text-(--text-secondary) w-20 shrink-0">
									{rec.source}
								</span>
								<span className="font-mono w-28 shrink-0 truncate">
									{rec.model || rec.provider}
								</span>
								<span className="text-yellow-400 w-20 shrink-0">
									{rec.kwh.toFixed(4)} kWh
								</span>
								<span className="text-red-400 w-16 shrink-0">
									{rec.co2G.toFixed(2)} g
								</span>
								<span className="text-(--text-secondary) ml-auto">
									{rec.durationS.toFixed(1)}s
								</span>
							</div>
						))}
					</div>
				</div>
			)}

			{report.summary && (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{report.summary}
				</p>
			)}
		</div>
	);
}
