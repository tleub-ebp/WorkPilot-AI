import type React from "react";
import { useTranslation } from "react-i18next";
import type {
	ConsensusResult,
	ConflictSeverity,
} from "../../../shared/types/consensus-arbiter";

const SEVERITY_STYLES: Record<ConflictSeverity, string> = {
	critical: "text-red-400 bg-red-500/10 border-red-500/20",
	high: "text-orange-400 bg-orange-500/10 border-orange-500/20",
	medium: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	low: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

interface ConsensusViewProps {
	readonly result?: ConsensusResult;
}

export function ConsensusView({
	result,
}: ConsensusViewProps): React.ReactElement {
	const { t } = useTranslation("consensusArbiter");
	if (!result) {
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
					{result.conflicts.length} {t("disagreements")} · {result.resolvedCount}{" "}
					{t("agreements")} · {result.escalatedCount} {t("escalated")}
				</p>
			</div>

			{result.allResolved ? (
				<div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
					✅ {t("allConflictsResolved")}
				</div>
			) : (
				<div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-sm">
					⚠️ {result.escalatedCount} {t("conflictsRequireHumanDecision")}
				</div>
			)}

			<div className="space-y-3">
				{result.conflicts.map((conflict, idx) => (
					<div
						key={`${conflict.topic}-${idx}`}
						className={`px-4 py-3 rounded-lg border ${SEVERITY_STYLES[conflict.severity]}`}
					>
						<div className="flex items-center justify-between mb-2">
							<p className="text-sm font-medium">{conflict.topic}</p>
							<div className="flex items-center gap-2">
								{conflict.strategyUsed && (
									<span className="text-xs opacity-70">
										{conflict.strategyUsed.replaceAll("_", " ")}
									</span>
								)}
								<span
									className={`px-2 py-0.5 rounded text-xs font-medium ${
										conflict.resolved
											? "bg-green-500/20 text-green-400"
											: "bg-yellow-500/20 text-yellow-400"
									}`}
								>
									{conflict.resolved ? t("resolved") : t("pending")}
								</span>
							</div>
						</div>

						{/* Agent opinions */}
						<div className="space-y-1 mb-2">
							{conflict.opinions.map((op) => (
								<div
									key={op.agentName}
									className="flex items-center gap-2 text-xs"
								>
									<span className="font-medium w-24 shrink-0">
										{op.agentName}
									</span>
									<span className="opacity-70 w-16 shrink-0">
										{op.domain}
									</span>
									<span className="flex-1 truncate">
										{op.recommendation}
									</span>
									<span className="opacity-70">
										{(op.confidence * 100).toFixed(0)}%
									</span>
								</div>
							))}
						</div>

						{conflict.resolution && (
							<p className="text-xs mt-1 text-green-400">
								→ {conflict.resolution}
							</p>
						)}
					</div>
				))}
			</div>

			{result.consensusSummary && (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{result.consensusSummary}
				</p>
			)}
		</div>
	);
}
