import { Trophy, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { BountyContestant } from "../../../preload/api/modules/bounty-board-api";

interface Props {
	readonly contestant: BountyContestant;
	readonly isWinner?: boolean;
	readonly rationale?: string;
}

const STATUS_STYLES: Record<BountyContestant["status"], string> = {
	queued: "bg-muted text-muted-foreground",
	running: "bg-blue-500/15 text-blue-500",
	completed: "bg-green-500/15 text-green-500",
	archived: "bg-zinc-500/15 text-zinc-500",
	error: "bg-red-500/15 text-red-500",
	winner: "bg-yellow-500/15 text-yellow-500",
};

export function ContestantCard({ contestant, isWinner, rationale }: Props) {
	const { t } = useTranslation(["bountyBoard", "common"]);
	const statusClass = STATUS_STYLES[contestant.status] ?? STATUS_STYLES.queued;

	return (
		<div
			className={`border rounded-md p-3 bg-card flex flex-col gap-2 ${isWinner ? "ring-2 ring-yellow-500/60" : ""}`}
		>
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-2">
					<span className="text-sm font-semibold">{contestant.label}</span>
					{isWinner && <Trophy className="w-4 h-4 text-yellow-500" />}
					{contestant.status === "error" && (
						<X className="w-4 h-4 text-red-500" />
					)}
				</div>
				<span
					className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${statusClass}`}
				>
					{t(`bountyBoard:status.${contestant.status}`, contestant.status)}
				</span>
			</div>

			<div className="text-xs text-muted-foreground">
				{contestant.provider}:{contestant.model}
			</div>

			<div className="grid grid-cols-3 gap-2 text-[11px]">
				<div>
					<div className="text-muted-foreground">
						{t("bountyBoard:metrics.score", "Score")}
					</div>
					<div className="font-mono font-semibold">
						{contestant.score != null ? contestant.score.toFixed(1) : "—"}
					</div>
				</div>
				<div>
					<div className="text-muted-foreground">
						{t("bountyBoard:metrics.tokens", "Tokens")}
					</div>
					<div className="font-mono">{contestant.tokens_used}</div>
				</div>
				<div>
					<div className="text-muted-foreground">
						{t("bountyBoard:metrics.duration", "Duration")}
					</div>
					<div className="font-mono">{contestant.duration_ms} ms</div>
				</div>
			</div>

			{Object.keys(contestant.quality_breakdown).length > 0 && (
				<div className="text-[10px] text-muted-foreground flex flex-wrap gap-2">
					{Object.entries(contestant.quality_breakdown).map(([k, v]) => (
						<span key={k} className="px-1.5 py-0.5 rounded bg-muted">
							{k}: {v}
						</span>
					))}
				</div>
			)}

			{rationale && (
				<div className="text-[11px] text-muted-foreground italic border-t border-border pt-2">
					{rationale}
				</div>
			)}

			{contestant.error && (
				<div className="text-[11px] text-red-500 border-t border-red-500/30 pt-2">
					{contestant.error}
				</div>
			)}
		</div>
	);
}
