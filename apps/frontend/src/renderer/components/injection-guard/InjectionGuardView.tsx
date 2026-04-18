import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupInjectionGuardListeners,
	useInjectionGuardStore,
} from "../../stores/injection-guard-store";
import type {
	InjectionScanResult,
	ScanFinding,
	ThreatLevel,
} from "../../../shared/types/injection-guard";

const THREAT_STYLES: Record<ThreatLevel, string> = {
	safe: "text-green-400 bg-green-500/10 border-green-500/20",
	suspect: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	blocked: "text-red-400 bg-red-500/10 border-red-500/20",
};

const SEVERITY_COLORS: Record<string, string> = {
	critical: "text-red-400",
	high: "text-orange-400",
	medium: "text-yellow-400",
	low: "text-blue-400",
};

interface InjectionGuardViewProps {
	readonly projectPath?: string;
}

function FindingRow({
	finding,
}: {
	readonly finding: ScanFinding;
}): React.ReactElement {
	return (
		<div className="flex items-center gap-2 text-xs">
			<span className="opacity-70 w-20 shrink-0">{finding.layer}</span>
			<span
				className={`font-medium w-20 shrink-0 ${SEVERITY_COLORS[finding.severity] ?? ""}`}
			>
				{finding.severity}
			</span>
			<span className="flex-1 truncate">{finding.description}</span>
			<span className="opacity-70">
				{(finding.confidence * 100).toFixed(0)}%
			</span>
		</div>
	);
}

function ResultCard({
	result,
	t,
}: {
	readonly result: InjectionScanResult;
	readonly t: (key: string) => string;
}): React.ReactElement {
	return (
		<div
			className={`px-4 py-3 rounded-lg border ${THREAT_STYLES[result.threatLevel]}`}
		>
			<div className="flex items-center justify-between mb-2">
				<p className="text-sm font-medium truncate">{result.source}</p>
				<span className="text-xs font-medium uppercase">
					{t(`threat.${result.threatLevel}`)}
				</span>
			</div>
			{result.findings.length > 0 ? (
				<div className="space-y-1">
					{result.findings.map((f) => (
						<FindingRow key={`${f.layer}-${f.description}`} finding={f} />
					))}
				</div>
			) : (
				<p className="text-xs opacity-70">{t("noFindings")}</p>
			)}
		</div>
	);
}

export function InjectionGuardView({
	projectPath,
}: InjectionGuardViewProps): React.ReactElement {
	const { t } = useTranslation("injectionGuard");

	useEffect(() => {
		const cleanup = setupInjectionGuardListeners();
		return cleanup;
	}, []);

	const phase = useInjectionGuardStore((s) => s.phase);
	const status = useInjectionGuardStore((s) => s.status);
	const results = useInjectionGuardStore((s) => s.results);
	const error = useInjectionGuardStore((s) => s.error);
	const startScan = useInjectionGuardStore((s) => s.startScan);
	const cancelScan = useInjectionGuardStore((s) => s.cancelScan);
	const reset = useInjectionGuardStore((s) => s.reset);

	const handleRun = (): void => {
		if (!projectPath) return;
		void startScan(projectPath);
	};

	const isScanning = phase === "scanning";

	const blocked = results.filter((r) => r.threatLevel === "blocked").length;
	const suspect = results.filter((r) => r.threatLevel === "suspect").length;
	const safe = results.filter((r) => r.threatLevel === "safe").length;

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
					<div className="grid grid-cols-3 gap-3">
						<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
							<p className="text-xs text-(--text-secondary)">
								{t("stats.blocked")}
							</p>
							<p className="text-2xl font-bold text-red-400">{blocked}</p>
						</div>
						<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
							<p className="text-xs text-(--text-secondary)">
								{t("stats.suspect")}
							</p>
							<p className="text-2xl font-bold text-yellow-400">{suspect}</p>
						</div>
						<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
							<p className="text-xs text-(--text-secondary)">
								{t("stats.safe")}
							</p>
							<p className="text-2xl font-bold text-green-400">{safe}</p>
						</div>
					</div>

					<div className="space-y-2">
						{results.map((result) => (
							<ResultCard
								key={result.source}
								result={result}
								t={t}
							/>
						))}
					</div>
				</>
			)}
		</div>
	);
}
