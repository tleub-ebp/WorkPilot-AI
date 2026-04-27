/**
 * #3.11 Agent Health Monitor panel.
 *
 * Lists every agent the monitor has heard about, with score / status /
 * suggested actions. Refresh button + reset button.
 */

import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAgentHealthStore } from "../../stores/phase35-stores";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { PanelShell } from "./_panel-shell";

const STATUS_COLOR: Record<string, string> = {
	healthy: "bg-green-500/20 text-green-700 border-green-500/40",
	degraded: "bg-amber-500/20 text-amber-700 border-amber-500/40",
	failing: "bg-orange-500/20 text-orange-700 border-orange-500/40",
	burned_out: "bg-red-500/20 text-red-700 border-red-500/40",
};

export function AgentHealthPanel() {
	const { t } = useTranslation("phase35");
	const { phase, error, scores, refresh, resetMonitor } = useAgentHealthStore();

	useEffect(() => {
		refresh();
	}, [refresh]);

	const isRunning = phase === "running";

	return (
		<PanelShell
			title={t("agentHealth.title")}
			subtitle={t("agentHealth.subtitle")}
			error={error}
			actions={
				<>
					<Button size="sm" variant="outline" onClick={() => refresh()} disabled={isRunning}>
						{t("agentHealth.refresh")}
					</Button>
					<Button size="sm" variant="ghost" onClick={() => resetMonitor()}>
						{t("agentHealth.reset")}
					</Button>
				</>
			}
		>
			{scores.length === 0 && !isRunning && (
				<p className="text-sm text-muted-foreground">{t("agentHealth.noAgents")}</p>
			)}
			<ul className="space-y-3">
				{scores.map((s) => (
					<li key={s.agent_name} className="rounded border p-3">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-3">
								<span className="font-mono font-medium">{s.agent_name}</span>
								<Badge className={STATUS_COLOR[s.status] ?? "bg-muted"}>
									{t(`agentHealth.status${s.status[0].toUpperCase()}${s.status.slice(1).replace("_o", "O")}` as never)}
								</Badge>
								<span className="text-2xl font-bold">{s.score.toFixed(0)}</span>
							</div>
							<span className="text-xs text-muted-foreground">
								{s.runs_in_window} {t("agentHealth.runs")} · {t(`agentHealth.trend${s.trend[0].toUpperCase()}${s.trend.slice(1)}` as never)}
							</span>
						</div>
						<div className="mt-2 grid grid-cols-4 gap-2 text-xs text-muted-foreground">
							<span>{t("agentHealth.successRate")}: {(s.success_rate * 100).toFixed(0)}%</span>
							<span>{t("agentHealth.errorRate")}: {(s.error_rate * 100).toFixed(0)}%</span>
							<span>{t("agentHealth.retryRate")}: {(s.retry_rate * 100).toFixed(0)}%</span>
							<span>{t("agentHealth.slowness")}: {s.slowness_ratio.toFixed(2)}×</span>
						</div>
						{s.actions.length > 0 && s.actions[0] !== "none" && (
							<div className="mt-2 flex flex-wrap gap-1">
								<span className="text-xs text-muted-foreground mr-2">{t("agentHealth.actions")}:</span>
								{s.actions.map((a) => (
									<Badge key={a} variant="outline" className="text-xs">
										{a}
									</Badge>
								))}
							</div>
						)}
					</li>
				))}
			</ul>
		</PanelShell>
	);
}
