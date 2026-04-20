import { DollarSign, Loader2, TrendingUp } from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import type { CostPrediction } from "../../../preload/api/modules/cost-predictor-api";
import { useCostPredictorStore } from "../../stores/cost-predictor-store";
import { Button } from "../ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "../ui/dialog";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

interface CostPredictorDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	projectPath: string;
	specId: string;
	onConfirm?: () => void;
}

function formatUsd(n: number): string {
	if (n < 0.01) return `$${n.toFixed(4)}`;
	if (n < 1) return `$${n.toFixed(3)}`;
	return `$${n.toFixed(2)}`;
}

function PredictionRow({
	prediction,
	highlighted,
}: {
	prediction: CostPrediction;
	highlighted?: boolean;
}) {
	return (
		<div
			className={`grid grid-cols-5 gap-2 text-sm py-2 px-3 border-b last:border-b-0 ${
				highlighted ? "bg-primary/5 font-medium" : ""
			}`}
		>
			<span className="col-span-2 truncate">
				<span className="text-muted-foreground">{prediction.provider}</span>{" "}
				{prediction.model}
			</span>
			<span className="font-mono text-right">
				{prediction.total_tokens.toLocaleString()}
			</span>
			<span className="font-mono text-right">
				{formatUsd(prediction.point_cost_usd)}
			</span>
			<span className="font-mono text-right text-xs text-muted-foreground">
				{formatUsd(prediction.low_cost_usd)}–{formatUsd(prediction.high_cost_usd)}
			</span>
		</div>
	);
}

export function CostPredictorDialog({
	open,
	onOpenChange,
	projectPath,
	specId,
	onConfirm,
}: CostPredictorDialogProps) {
	const { t } = useTranslation(["costPredictor", "common"]);
	const {
		report,
		loading,
		error,
		provider,
		model,
		compare,
		thinking,
		setProvider,
		setModel,
		setCompare,
		setThinking,
		run,
		reset,
	} = useCostPredictorStore();

	useEffect(() => {
		if (open && projectPath && specId && !report && !loading) {
			run(projectPath, specId);
		}
	}, [open, projectPath, specId, report, loading, run]);

	useEffect(() => {
		if (!open) reset();
	}, [open, reset]);

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-2xl">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<DollarSign className="w-5 h-5" />
						{t("costPredictor:title", "Cost prediction")}
					</DialogTitle>
					<DialogDescription>
						{t(
							"costPredictor:description",
							"Expected token usage and USD cost before running this spec.",
						)}
					</DialogDescription>
				</DialogHeader>

				<div className="grid grid-cols-2 gap-3">
					<div>
						<Label className="text-xs">
							{t("costPredictor:provider", "Provider")}
						</Label>
						<Input
							value={provider}
							onChange={(e) => setProvider(e.target.value)}
						/>
					</div>
					<div>
						<Label className="text-xs">
							{t("costPredictor:model", "Model")}
						</Label>
						<Input value={model} onChange={(e) => setModel(e.target.value)} />
					</div>
					<div className="col-span-2">
						<Label className="text-xs">
							{t(
								"costPredictor:compareModels",
								"Compare models (provider:model,provider:model)",
							)}
						</Label>
						<Input
							value={compare}
							onChange={(e) => setCompare(e.target.value)}
							placeholder="anthropic:claude-haiku-4-5-20251001"
						/>
					</div>
					<label className="flex items-center gap-2 col-span-2 text-sm">
						<input
							type="checkbox"
							checked={thinking}
							onChange={(e) => setThinking(e.target.checked)}
						/>
						{t("costPredictor:thinking", "Include extended thinking tokens")}
					</label>
				</div>

				<div className="flex items-center gap-2">
					<Button
						size="sm"
						onClick={() => run(projectPath, specId)}
						disabled={loading}
					>
						{loading ? (
							<Loader2 className="w-4 h-4 animate-spin mr-2" />
						) : (
							<TrendingUp className="w-4 h-4 mr-2" />
						)}
						{t("costPredictor:predict", "Predict")}
					</Button>
				</div>

				{error && <p className="text-sm text-destructive">{error}</p>}

				{report && (
					<div className="border rounded-md overflow-hidden bg-card">
						<div className="grid grid-cols-5 gap-2 text-xs text-muted-foreground py-2 px-3 border-b bg-muted/30">
							<span className="col-span-2">
								{t("costPredictor:modelCol", "Model")}
							</span>
							<span className="text-right">
								{t("costPredictor:tokens", "Tokens")}
							</span>
							<span className="text-right">
								{t("costPredictor:cost", "Cost")}
							</span>
							<span className="text-right">
								{t("costPredictor:band", "±Band")}
							</span>
						</div>
						<PredictionRow prediction={report.selected} highlighted />
						{report.alternatives.map((alt) => (
							<PredictionRow
								key={`${alt.provider}-${alt.model}`}
								prediction={alt}
							/>
						))}
						<div className="px-3 py-2 text-xs text-muted-foreground bg-muted/20">
							{t("costPredictor:footprint", {
								subtasks: report.footprint.subtasks,
								files: report.footprint.files_touched,
								lines: report.footprint.lines_in_scope,
								defaultValue:
									"{{subtasks}} subtask(s), {{files}} file(s), ~{{lines}} lines. ",
							})}
							{t("costPredictor:history", {
								n: report.history_sample_count,
								defaultValue: "Based on {{n}} historical sample(s).",
							})}
						</div>
						{report.selected.notes.length > 0 && (
							<ul className="list-disc pl-6 text-xs text-muted-foreground px-3 py-2">
								{report.selected.notes.map((note) => (
									<li key={note}>{note}</li>
								))}
							</ul>
						)}
					</div>
				)}

				<DialogFooter>
					<Button variant="outline" onClick={() => onOpenChange(false)}>
						{t("common:cancel", "Cancel")}
					</Button>
					{onConfirm && (
						<Button
							onClick={() => {
								onConfirm();
								onOpenChange(false);
							}}
							disabled={!report}
						>
							{t("costPredictor:confirmRun", "Run build anyway")}
						</Button>
					)}
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
