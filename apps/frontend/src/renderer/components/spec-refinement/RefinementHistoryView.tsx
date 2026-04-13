import type React from "react";
import { useTranslation } from "react-i18next";
import type { RefinementHistory } from "../../../shared/types/spec-refinement";

interface RefinementHistoryViewProps {
	readonly history?: RefinementHistory;
}

export function RefinementHistoryView({
	history,
}: RefinementHistoryViewProps): React.ReactElement {
	const { t } = useTranslation("specRefinement");
	if (!history) {
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
					Spec {history.specId} · {t("iterations", { num: history.currentIteration })} ·{" "}
					{history.status}
				</p>
			</div>

			{/* Convergence indicator */}
			<div
				className={`p-3 rounded-lg border ${
					history.isConverging
						? "bg-green-500/10 border-green-500/20 text-green-400"
						: "bg-yellow-500/10 border-yellow-500/20 text-yellow-400"
				}`}
			>
				<div className="flex items-center justify-between">
					<span className="text-sm font-medium">
						{history.isConverging ? "✅ Converging" : "⚠️ Diverging"}
					</span>
					<span className="text-xs">
						Score: {(history.convergenceScore * 100).toFixed(0)}%
					</span>
				</div>
			</div>

			{/* Timeline */}
			<div className="space-y-3">
				{history.iterations.map((iteration) => (
					<div
						key={iteration.iteration}
						className="px-4 py-3 rounded-lg border border-(--border-color) hover:bg-(--bg-secondary) transition-colors"
					>
						<div className="flex items-center justify-between mb-2">
							<p className="text-sm font-medium">
								{t("iteration")}: #{iteration.iteration}
							</p>
							<span
								className={`text-xs ${(() => {
									if (iteration.qualityScore >= 0.8) {
										return "text-green-400";
									}
									if (iteration.qualityScore >= 0.5) {
										return "text-yellow-400";
									}
									return "text-red-400";
								})()}`}
							>
								{t("qualityScore")}: {(iteration.qualityScore * 100).toFixed(0)}%
							</span>
						</div>

						{/* Signals */}
						{iteration.signals.length > 0 && (
							<div className="flex flex-wrap gap-1 mb-2">
								{iteration.signals.map((signal) => (
									<span
										key={`${iteration.iteration}-${signal.signalType}`}
										className="px-1.5 py-0.5 rounded text-xs bg-blue-500/10 text-blue-400"
									>
										{t("signals")}: {signal.signalType.replaceAll("_", " ")}
									</span>
								))}
							</div>
						)}

						{/* Changes */}
						{iteration.changesMade.length > 0 && (
							<ul className="text-xs text-(--text-secondary) space-y-0.5">
								{iteration.changesMade.map((change) => (
									<li key={`${iteration.iteration}-${change}`}>• {t("changes")}: {change}</li>
								))}
							</ul>
						)}
					</div>
				))}
			</div>

			{history.summary && (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{history.summary}
				</p>
			)}
		</div>
	);
}
