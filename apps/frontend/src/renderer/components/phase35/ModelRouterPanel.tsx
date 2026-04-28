/**
 * #3.1 Adaptive Model Routing panel.
 *
 * Type a prompt + optional task class hint, see (a) the chosen model
 * and (b) a "what would it cost on each tier" comparison table.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useModelRouterStore } from "../../stores/phase35-stores";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { PanelShell } from "./_panel-shell";

export function ModelRouterPanel() {
	const { t } = useTranslation("phase35");
	const { phase, error, chosen, comparison, route, compare } = useModelRouterStore();
	const [prompt, setPrompt] = useState("");
	const [hint, setHint] = useState("");
	const [providers, setProviders] = useState("anthropic, openai");

	const isRunning = phase === "running";

	const buildReq = () => ({
		prompt,
		hint: hint || undefined,
		available: providers
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean),
	});

	return (
		<PanelShell
			title={t("modelRouter.title")}
			subtitle={t("modelRouter.subtitle")}
			error={error}
			actions={
				<>
					<Button
						size="sm"
						onClick={() => route(buildReq())}
						disabled={isRunning || !prompt.trim()}
					>
						{isRunning ? t("common.running") : t("common.run")}
					</Button>
					<Button
						size="sm"
						variant="outline"
						onClick={() => compare(buildReq())}
						disabled={isRunning || !prompt.trim()}
					>
						{t("modelRouter.compare")}
					</Button>
				</>
			}
		>
			<div className="space-y-3">
				<div>
					<label htmlFor="prompt-input" className="block text-sm font-medium mb-1">
						{t("modelRouter.prompt")}
					</label>
					<textarea
						id="prompt-input"
						value={prompt}
						onChange={(e) => setPrompt(e.target.value)}
						rows={3}
						className="w-full rounded border bg-background p-2 text-sm font-mono"
						placeholder="rename foo to bar"
					/>
				</div>
				<div className="grid grid-cols-2 gap-3">
					<div>
						<label htmlFor="hint-input" className="block text-sm font-medium mb-1">
							{t("modelRouter.hint")}
						</label>
						<input
							id="hint-input"
							value={hint}
							onChange={(e) => setHint(e.target.value)}
							className="w-full rounded border bg-background p-2 text-sm"
							placeholder={t("modelRouter.hintPlaceholder")}
						/>
					</div>
					<div>
						<label htmlFor="providers-input" className="block text-sm font-medium mb-1">
							{t("modelRouter.availableProviders")}
						</label>
						<input
							id="providers-input"
							value={providers}
							onChange={(e) => setProviders(e.target.value)}
							className="w-full rounded border bg-background p-2 text-sm font-mono"
						/>
					</div>
				</div>

				{chosen && (
					<div className="rounded border p-3 text-sm space-y-1">
						<div>
							<span className="font-medium">{t("modelRouter.chosen")}: </span>
							<Badge variant="outline">{chosen.provider}</Badge>{" "}
							<code>{chosen.model}</code> ({chosen.tier})
						</div>
						<div className="text-muted-foreground">
							{t("modelRouter.estimatedCost")}: ${chosen.estimated_cost_usd.toFixed(6)}
						</div>
						<div className="text-xs text-muted-foreground">
							{t("modelRouter.reason")}: {chosen.reason}
						</div>
					</div>
				)}

				{comparison && (
					<table className="w-full text-sm border">
						<thead>
							<tr className="border-b bg-muted/40">
								<th className="text-left p-2">tier</th>
								<th className="text-left p-2">model</th>
								<th className="text-right p-2">$ / call</th>
							</tr>
						</thead>
						<tbody>
							{Object.entries(comparison).map(([tier, c]) => (
								<tr key={tier} className="border-b">
									<td className="p-2">{tier}</td>
									<td className="p-2 font-mono">
										{c.provider}/{c.model}
									</td>
									<td className="p-2 text-right">${c.estimated_cost_usd.toFixed(6)}</td>
								</tr>
							))}
						</tbody>
					</table>
				)}
			</div>
		</PanelShell>
	);
}
