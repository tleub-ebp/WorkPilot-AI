import type React from "react";
import { useTranslation } from "react-i18next";
import type { CarbonReport } from "../../../shared/types/carbon-profiler";

interface CarbonReportViewProps {
	readonly report?: CarbonReport;
}

export function CarbonReportView({
	report,
}: CarbonReportViewProps): React.ReactElement {
	const { t } = useTranslation("carbonProfiler");
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
					{report.periodStart} → {report.periodEnd}
				</p>
			</div>

			{/* Top-level stats */}
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

			{/* By provider breakdown */}
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

			{/* By model breakdown */}
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

			{/* Records table */}
			<div>
				<h3 className="text-sm font-medium text-(--text-secondary) mb-2">
					{t("recentRecords")}
				</h3>
				<div className="space-y-1">
					{report.records.slice(0, 20).map((rec, idx) => (
						<div
							key={`${rec.timestamp}-${idx}`}
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
