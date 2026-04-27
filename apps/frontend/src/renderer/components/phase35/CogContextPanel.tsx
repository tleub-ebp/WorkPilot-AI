/**
 * #3.2 Cognitive Context Optimizer panel.
 *
 * Paste a prompt + a list of candidate files + a token budget → see which
 * files were included, with their relevance scores and truncation status.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useCogContextStore } from "../../stores/phase35-stores";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { PanelShell } from "./_panel-shell";

export function CogContextPanel() {
	const { t } = useTranslation("phase35");
	const { phase, error, context, optimize } = useCogContextStore();
	const [prompt, setPrompt] = useState("");
	const [files, setFiles] = useState("");
	const [budget, setBudget] = useState(8000);

	const isRunning = phase === "running";

	const handleRun = () => {
		const list = files
			.split("\n")
			.map((s) => s.trim())
			.filter(Boolean);
		optimize(prompt, list, budget);
	};

	return (
		<PanelShell
			title={t("cogContext.title")}
			subtitle={t("cogContext.subtitle")}
			error={error}
			actions={
				<Button
					size="sm"
					onClick={handleRun}
					disabled={isRunning || !files.trim()}
				>
					{isRunning ? t("common.running") : t("cogContext.optimize")}
				</Button>
			}
		>
			<div className="space-y-3 text-sm">
				<div>
					<label className="block font-medium mb-1">
						{t("cogContext.prompt")}
					</label>
					<textarea
						value={prompt}
						onChange={(e) => setPrompt(e.target.value)}
						rows={2}
						className="w-full rounded border bg-background p-2 text-sm"
					/>
				</div>
				<div className="grid grid-cols-3 gap-3">
					<div className="col-span-2">
						<label className="block font-medium mb-1">
							{t("cogContext.candidateFiles")}
						</label>
						<textarea
							value={files}
							onChange={(e) => setFiles(e.target.value)}
							rows={5}
							className="w-full rounded border bg-background p-2 font-mono text-xs"
							placeholder="/abs/path/file1.py&#10;/abs/path/file2.py"
						/>
					</div>
					<div>
						<label className="block font-medium mb-1">
							{t("cogContext.tokenBudget")}
						</label>
						<input
							type="number"
							value={budget}
							onChange={(e) => setBudget(Number.parseInt(e.target.value, 10) || 0)}
							className="w-full rounded border bg-background p-2 text-sm"
						/>
					</div>
				</div>

				{context && (
					<div className="space-y-2">
						<div className="flex flex-wrap gap-2">
							<Badge variant="outline">
								{t("cogContext.included")}: {context.slices.length}
							</Badge>
							<Badge variant="outline">
								{t("cogContext.skipped")}: {context.files_skipped.length}
							</Badge>
							<Badge variant="outline">
								{t("cogContext.fillRatio")}:{" "}
								{((context.tokens_used / context.token_budget) * 100).toFixed(0)}%
							</Badge>
						</div>
						<table className="w-full text-sm border">
							<thead>
								<tr className="border-b bg-muted/40">
									<th className="text-left p-2">file</th>
									<th className="text-right p-2">score</th>
									<th className="text-right p-2">tokens</th>
									<th className="p-2">truncated</th>
								</tr>
							</thead>
							<tbody>
								{context.slices.map((s) => (
									<tr key={s.file_path} className="border-b">
										<td className="p-2 font-mono text-xs truncate max-w-md">
											{s.file_path}
										</td>
										<td className="p-2 text-right">
											{s.relevance.score.toFixed(2)}
										</td>
										<td className="p-2 text-right">
											{s.included_tokens}/{s.full_size_tokens}
										</td>
										<td className="p-2 text-center">{s.truncated ? "✂" : ""}</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				)}
			</div>
		</PanelShell>
	);
}
