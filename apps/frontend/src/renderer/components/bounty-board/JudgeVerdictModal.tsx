import { Trophy } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { BountyResult } from "../../../preload/api/modules/bounty-board-api";
import { Button } from "../ui/button";

interface Props {
	readonly result: BountyResult;
	readonly onClose: () => void;
}

export function JudgeVerdictModal({ result, onClose }: Props) {
	const { t } = useTranslation(["bountyBoard", "common"]);
	const winner = result.contestants.find((c) => c.id === result.winnerId) ?? null;

	const sorted = [...result.contestants].sort(
		(a, b) => (b.score ?? -1) - (a.score ?? -1),
	);

	return (
		<div
			className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
			onClick={onClose}
			onKeyDown={(e) => {
				if (e.key === "Escape") onClose();
			}}
			role="dialog"
			aria-modal="true"
			tabIndex={-1}
		>
			<div
				className="bg-background border rounded-lg shadow-xl max-w-2xl w-full p-5 flex flex-col gap-4"
				onClick={(e) => e.stopPropagation()}
				onKeyDown={(e) => e.stopPropagation()}
				role="document"
			>
				<div className="flex items-center gap-2">
					<Trophy className="w-5 h-5 text-yellow-500" />
					<h2 className="text-lg font-semibold">
						{t("bountyBoard:verdict.title", "Judge verdict")}
					</h2>
				</div>

				{winner ? (
					<div className="border border-yellow-500/30 rounded-md p-3 bg-yellow-500/5">
						<div className="text-sm">
							{t("bountyBoard:verdict.winnerIs", "Winner:")}
						</div>
						<div className="text-xl font-semibold">
							{winner.label} — {winner.provider}:{winner.model}
						</div>
						<div className="text-xs text-muted-foreground mt-1">
							{t("bountyBoard:metrics.score", "Score")}:{" "}
							{winner.score?.toFixed(1) ?? "—"}
						</div>
					</div>
				) : (
					<div className="border rounded-md p-3 text-sm">
						{t(
							"bountyBoard:verdict.noWinner",
							"No contestant met the acceptance criteria.",
						)}
					</div>
				)}

				<div>
					<h3 className="text-sm font-semibold mb-2">
						{t("bountyBoard:verdict.ranking", "Ranking")}
					</h3>
					<table className="w-full text-xs">
						<thead>
							<tr className="text-left text-muted-foreground border-b">
								<th className="py-1">#</th>
								<th className="py-1">
									{t("bountyBoard:verdict.contestant", "Contestant")}
								</th>
								<th className="py-1">
									{t("bountyBoard:metrics.score", "Score")}
								</th>
								<th className="py-1">
									{t("bountyBoard:verdict.rationale", "Rationale")}
								</th>
							</tr>
						</thead>
						<tbody>
							{sorted.map((c, idx) => (
								<tr key={c.id} className="border-b last:border-0">
									<td className="py-2 font-mono">{idx + 1}</td>
									<td className="py-2">
										{c.label}{" "}
										<span className="text-muted-foreground">
											({c.provider}:{c.model})
										</span>
									</td>
									<td className="py-2 font-mono">
										{c.score != null ? c.score.toFixed(1) : "—"}
									</td>
									<td className="py-2 text-muted-foreground">
										{result.judgeRationale[c.id] ?? "—"}
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>

				<div className="flex justify-end">
					<Button size="sm" onClick={onClose}>
						{t("common:close", "Close")}
					</Button>
				</div>
			</div>
		</div>
	);
}
