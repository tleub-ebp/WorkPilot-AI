/**
 * #3.4 CI/CD Anomaly Detective panel.
 *
 * Paste a CI log → see detected signals (kind / severity / suggested fix)
 * + recurring patterns when multiple logs were analysed.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useCicdAnomalyStore } from "../../stores/phase35-stores";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { PanelShell } from "./_panel-shell";

const SEV_COLOR: Record<string, string> = {
	critical: "bg-red-500/20 text-red-700 border-red-500/40",
	high: "bg-orange-500/20 text-orange-700 border-orange-500/40",
	medium: "bg-amber-500/20 text-amber-700 border-amber-500/40",
	low: "bg-muted text-muted-foreground",
};

export function CicdAnomalyPanel() {
	const { t } = useTranslation("phase35");
	const { phase, error, signals, scan } = useCicdAnomalyStore();
	const [log, setLog] = useState("");

	const isRunning = phase === "running";

	return (
		<PanelShell
			title={t("cicdAnomaly.title")}
			subtitle={t("cicdAnomaly.subtitle")}
			error={error}
			actions={
				<Button
					size="sm"
					onClick={() => scan(log)}
					disabled={isRunning || !log.trim()}
				>
					{isRunning ? t("common.running") : t("cicdAnomaly.scan")}
				</Button>
			}
		>
			<div className="space-y-3">
				<div>
					<label className="block text-sm font-medium mb-1">
						{t("cicdAnomaly.logLabel")}
					</label>
					<textarea
						value={log}
						onChange={(e) => setLog(e.target.value)}
						rows={10}
						className="w-full rounded border bg-background p-2 text-xs font-mono"
						placeholder="Paste your CI log here…"
					/>
				</div>

				{signals.length > 0 && (
					<div>
						<div className="mb-2 font-medium text-sm">
							{t("cicdAnomaly.signals")} ({signals.length})
						</div>
						<ul className="space-y-2 text-sm">
							{signals.map((s, i) => (
								<li key={i} className="rounded border p-2">
									<div className="flex items-center gap-2">
										<Badge className={SEV_COLOR[s.severity] ?? "bg-muted"}>
											{s.severity}
										</Badge>
										<span className="font-mono text-xs">{s.kind}</span>
										<span className="text-xs text-muted-foreground">
											line {s.line_number}
										</span>
									</div>
									<div className="mt-1 font-mono text-xs text-muted-foreground truncate">
										{s.matching_line}
									</div>
									<div className="mt-1 text-xs">
										<span className="font-medium">→ </span>
										{s.suggested_fix}
									</div>
								</li>
							))}
						</ul>
					</div>
				)}
			</div>
		</PanelShell>
	);
}
