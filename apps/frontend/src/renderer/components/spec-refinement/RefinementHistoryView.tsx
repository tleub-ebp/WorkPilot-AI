import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupSpecRefinementListeners,
	useSpecRefinementStore,
} from "../../stores/spec-refinement-store";
import type { RefinementHistory } from "../../../shared/types/spec-refinement";

interface RefinementHistoryViewProps {
	readonly projectPath?: string;
}

function HistoryCard({
	history,
	t,
}: {
	history: RefinementHistory;
	t: (key: string, options?: Record<string, unknown>) => string;
}): React.ReactElement {
	return (
		<div className="flex flex-col gap-3 p-4 rounded-lg border border-(--border-color) bg-(--bg-secondary)">
			<div>
				<h3 className="text-base font-semibold">
					Spec {history.specId}
				</h3>
				<p className="text-sm text-(--text-secondary)">
					{t("iterations", { num: history.currentIteration })} · {history.status}
				</p>
			</div>

			<div
				className={`p-3 rounded-lg border ${
					history.isConverging
						? "bg-green-500/10 border-green-500/20 text-green-400"
						: "bg-yellow-500/10 border-yellow-500/20 text-yellow-400"
				}`}
			>
				<div className="flex items-center justify-between">
					<span className="text-sm font-medium">
						{history.isConverging ? t("converging") : t("diverging")}
					</span>
					<span className="text-xs">
						{t("score")}: {(history.convergenceScore * 100).toFixed(0)}%
					</span>
				</div>
			</div>

			<div className="space-y-2">
				{history.iterations.map((iteration) => (
					<div
						key={iteration.iteration}
						className="px-3 py-2 rounded-md border border-(--border-color) hover:bg-(--bg-primary) transition-colors"
					>
						<div className="flex items-center justify-between mb-1">
							<p className="text-sm font-medium">
								{t("iteration")}: #{iteration.iteration}
							</p>
							<span
								className={`text-xs ${(() => {
									if (iteration.qualityScore >= 0.8) return "text-green-400";
									if (iteration.qualityScore >= 0.5) return "text-yellow-400";
									return "text-red-400";
								})()}`}
							>
								{t("qualityScore")}: {(iteration.qualityScore * 100).toFixed(0)}%
							</span>
						</div>

						{iteration.signals.length > 0 && (
							<div className="flex flex-wrap gap-1 mb-1">
								{iteration.signals.map((signal, idx) => (
									<span
										key={`${iteration.iteration}-${signal.signalType}-${idx}`}
										className="px-1.5 py-0.5 rounded text-xs bg-blue-500/10 text-blue-400"
									>
										{signal.signalType.replaceAll("_", " ")}
									</span>
								))}
							</div>
						)}

						{iteration.changesMade.length > 0 && (
							<ul className="text-xs text-(--text-secondary) space-y-0.5">
								{iteration.changesMade.map((change, idx) => (
									<li key={`${iteration.iteration}-${idx}`}>• {change}</li>
								))}
							</ul>
						)}
					</div>
				))}
			</div>

			{history.summary && (
				<p className="text-xs text-(--text-secondary) italic">
					{history.summary}
				</p>
			)}
		</div>
	);
}

export function RefinementHistoryView({
	projectPath,
}: RefinementHistoryViewProps): React.ReactElement {
	const { t } = useTranslation("specRefinement");

	useEffect(() => {
		const cleanup = setupSpecRefinementListeners();
		return cleanup;
	}, []);

	const phase = useSpecRefinementStore((s) => s.phase);
	const status = useSpecRefinementStore((s) => s.status);
	const histories = useSpecRefinementStore((s) => s.histories);
	const error = useSpecRefinementStore((s) => s.error);
	const startScan = useSpecRefinementStore((s) => s.startScan);
	const cancelScan = useSpecRefinementStore((s) => s.cancelScan);
	const reset = useSpecRefinementStore((s) => s.reset);

	const handleRun = (): void => {
		if (!projectPath) return;
		void startScan(projectPath);
	};

	const isScanning = phase === "scanning";

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
				<p className="text-sm text-red-400">
					{t("errors.failed", { error })}
				</p>
			)}

			{phase === "complete" && histories.length === 0 && (
				<p className="text-sm text-(--text-secondary)">{t("noData")}</p>
			)}

			{histories.length > 0 && (
				<div className="flex flex-col gap-4">
					{histories.map((history) => (
						<HistoryCard key={history.specId} history={history} t={t} />
					))}
				</div>
			)}
		</div>
	);
}
