import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupRegressionGuardianListeners,
	useRegressionGuardianStore,
} from "../../stores/regression-guardian-store";
import type {
	Incident,
	RegressionGuardianResult,
} from "../../../shared/types/regression-guardian";

const SEVERITY_COLORS: Record<string, string> = {
	critical: "text-red-400 bg-red-500/10 border-red-500/20",
	error: "text-orange-400 bg-orange-500/10 border-orange-500/20",
	warning: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	info: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

interface RegressionGuardianDashboardProps {
	readonly projectPath?: string;
	readonly onViewTest?: (result: RegressionGuardianResult) => void;
}

function StatCard({
	label,
	value,
	color,
}: {
	readonly label: string;
	readonly value: number;
	readonly color: string;
}): React.ReactElement {
	return (
		<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
			<p className="text-xs text-(--text-secondary)">{label}</p>
			<p className={`text-2xl font-bold ${color}`}>{value}</p>
		</div>
	);
}

function IncidentRow({
	incident,
	hasTest,
	isDuplicate,
	onView,
	t,
}: {
	readonly incident: Incident;
	readonly hasTest: boolean;
	readonly isDuplicate: boolean;
	readonly onView: () => void;
	readonly t: (key: string) => string;
}): React.ReactElement {
	let actionContent: React.ReactNode;
	if (isDuplicate) {
		actionContent = (
			<span className="text-xs text-yellow-400">{t("duplicate")}</span>
		);
	} else if (hasTest) {
		actionContent = (
			<button
				type="button"
				onClick={onView}
				className="px-3 py-1 text-xs rounded bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"
			>
				{t("viewTest")}
			</button>
		);
	} else {
		actionContent = (
			<span className="text-xs text-(--text-secondary)">{t("noTest")}</span>
		);
	}

	return (
		<div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-(--border-color) hover:bg-(--bg-secondary) transition-colors">
			<span
				className={`px-2 py-0.5 rounded text-xs font-medium border ${SEVERITY_COLORS[incident.severity] ?? ""}`}
			>
				{incident.severity}
			</span>
			<div className="flex-1 min-w-0">
				<p className="text-sm font-medium truncate">{incident.title}</p>
				<p className="text-xs text-(--text-secondary)">
					{incident.source} · {incident.exceptionType || "unknown"}
				</p>
			</div>
			{actionContent}
		</div>
	);
}

export function RegressionGuardianDashboard({
	projectPath,
	onViewTest,
}: RegressionGuardianDashboardProps): React.ReactElement {
	const { t } = useTranslation("regressionGuardian");

	useEffect(() => {
		const cleanup = setupRegressionGuardianListeners();
		return cleanup;
	}, []);

	const phase = useRegressionGuardianStore((s) => s.phase);
	const status = useRegressionGuardianStore((s) => s.status);
	const results = useRegressionGuardianStore((s) => s.results);
	const error = useRegressionGuardianStore((s) => s.error);
	const startScan = useRegressionGuardianStore((s) => s.startScan);
	const cancelScan = useRegressionGuardianStore((s) => s.cancelScan);
	const reset = useRegressionGuardianStore((s) => s.reset);

	const handleRun = (): void => {
		if (!projectPath) return;
		void startScan(projectPath);
	};

	const isScanning = phase === "scanning";

	const generated = results.filter((r) => r.generatedTest && !r.isDuplicate);
	const duplicates = results.filter((r) => r.isDuplicate);

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div className="flex items-center justify-between">
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<div className="flex gap-2">
					{!isScanning && (
						<button
							type="button"
							onClick={handleRun}
							disabled={!projectPath}
							className="px-3 py-1.5 rounded-md bg-blue-500 hover:bg-blue-600 disabled:bg-gray-500 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
						>
							{t("actions.runScan")}
						</button>
					)}
					{isScanning && (
						<button
							type="button"
							onClick={() => void cancelScan()}
							className="px-3 py-1.5 rounded-md bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors"
						>
							{t("actions.cancel")}
						</button>
					)}
					{phase === "complete" && (
						<button
							type="button"
							onClick={reset}
							className="px-3 py-1.5 rounded-md border border-(--border-color) hover:bg-(--bg-secondary) text-sm font-medium transition-colors"
						>
							{t("actions.reset")}
						</button>
					)}
				</div>
			</div>

			{!projectPath && (
				<p className="text-sm text-(--text-secondary)">
					{t("errors.noProject")}
				</p>
			)}

			{isScanning && (
				<p className="text-sm text-(--text-secondary)">
					{status || t("actions.scanning")}
				</p>
			)}

			{phase === "error" && error && (
				<p className="text-sm text-red-400">{error}</p>
			)}

			{phase === "complete" && results.length === 0 && (
				<p className="text-sm text-(--text-secondary)">{t("noData")}</p>
			)}

			{results.length > 0 && (
				<>
					<p className="text-sm text-(--text-secondary)">
						{t("incidentsDetected", { count: results.length })}
					</p>

					<div className="grid grid-cols-3 gap-3">
						<StatCard
							label={t("stats.incidents")}
							value={results.length}
							color="text-blue-400"
						/>
						<StatCard
							label={t("stats.testsGenerated")}
							value={generated.length}
							color="text-green-400"
						/>
						<StatCard
							label={t("stats.duplicatesSkipped")}
							value={duplicates.length}
							color="text-yellow-400"
						/>
					</div>

					<div className="space-y-2">
						{results.map((result) => (
							<IncidentRow
								key={result.incident.id}
								incident={result.incident}
								hasTest={!!result.generatedTest}
								isDuplicate={result.isDuplicate}
								onView={() => onViewTest?.(result)}
								t={t}
							/>
						))}
					</div>
				</>
			)}
		</div>
	);
}
