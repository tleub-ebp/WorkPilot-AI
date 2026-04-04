import {
	AlertTriangle,
	Check,
	Copy,
	Loader2,
	RefreshCw,
	Shield,
	TrendingUp,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { AutoRefactorResult } from "../../stores/auto-refactor-store";
import {
	cancelAutoRefactor,
	setupAutoRefactorListeners,
	startAutoRefactor,
	useAutoRefactorStore,
} from "../../stores/auto-refactor-store";
import { useProjectStore } from "../../stores/project-store";
import { Button } from "../ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "../ui/dialog";
import { Label } from "../ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { Switch } from "../ui/switch";

const MODELS = [
	"claude-4.6-sonnet",
	"claude-4.5-sonnet",
	"claude-4.6-opus",
	"gpt-5",
	"gpt-5.1",
	"gpt-4.1",
	"gemini-2.5-pro",
	"deepseek-r1",
] as const;
const THINKING_LEVELS = [
	"none",
	"low",
	"medium",
	"high",
	"ultrathink",
] as const;

/**
 * AutoRefactorDialog — AI-powered automatic refactoring dialog.
 *
 * Shows a dialog where users can analyze their codebase for code smells,
 * technical debt, and outdated patterns, then generate and execute refactoring plans.
 *
 * Usage:
 *   const { openDialog, closeDialog, isOpen } = useAutoRefactorStore();
 *   <AutoRefactorDialog />
 */
export function AutoRefactorDialog() {
	const { t } = useTranslation(["autoRefactor", "common"]);
	const [copied, setCopied] = useState(false);
	const streamOutputRef = useRef<HTMLPreElement>(null);

	const {
		isOpen,
		closeDialog,
		phase,
		status,
		streamingOutput,
		result,
		executionResult,
		error,
		autoExecute,
		model,
		thinkingLevel,
		setAutoExecute,
		setModel,
		setThinkingLevel,
		reset,
	} = useAutoRefactorStore();

	const selectedProjectId = useProjectStore((s) => s.selectedProjectId);

	// Setup IPC listeners once
	useEffect(() => {
		const cleanup = setupAutoRefactorListeners();
		return cleanup;
	}, []);

	// Auto-scroll streaming output
	useEffect(() => {
		if (streamOutputRef.current) {
			streamOutputRef.current.scrollTop = streamOutputRef.current.scrollHeight;
		}
	}, []);

	const handleStart = useCallback(() => {
		if (!selectedProjectId) return;
		startAutoRefactor(selectedProjectId);
	}, [selectedProjectId]);

	const handleCancel = useCallback(() => {
		cancelAutoRefactor();
	}, []);

	const handleCopy = useCallback(async (text: string) => {
		try {
			await navigator.clipboard.writeText(text);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch {
			// Clipboard not available
		}
	}, []);

	const handleClose = useCallback(() => {
		if (phase === "analyzing" || phase === "executing") {
			handleCancel();
		}
		closeDialog();
	}, [phase, closeDialog, handleCancel]);

	const handleTryAgain = useCallback(() => {
		reset();
		useAutoRefactorStore.setState({
			isOpen: true,
			autoExecute,
			model,
			thinkingLevel,
		});
	}, [reset, autoExecute, model, thinkingLevel]);

	const isAnalyzing = phase === "analyzing";
	const isExecuting = phase === "executing";
	const isComplete = phase === "complete";
	const isError = phase === "error";
	const canStart = selectedProjectId && !isAnalyzing && !isExecuting;

	return (
		<Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
			<DialogContent className="sm:max-w-[800px] max-h-[90vh] flex flex-col">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<RefreshCw className="h-5 w-5 text-primary" />
						{t("autoRefactor:title")}
					</DialogTitle>
					<DialogDescription>{t("autoRefactor:description")}</DialogDescription>
				</DialogHeader>

				<div className="flex-1 overflow-y-auto space-y-4 py-2">
					{/* Configuration */}
					<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
						{/* Auto Execute Switch */}
						<div className="space-y-2">
							<Label htmlFor="auto-execute" className="flex items-center gap-2">
								<Zap className="h-4 w-4" />
								{t("autoRefactor:config.autoExecute.label")}
							</Label>
							<div className="flex items-center space-x-2">
								<Switch
									id="auto-execute"
									checked={autoExecute}
									onCheckedChange={setAutoExecute}
									disabled={isAnalyzing || isExecuting}
								/>
								<Label
									htmlFor="auto-execute"
									className="text-sm text-muted-foreground"
								>
									{autoExecute
										? t("autoRefactor:config.autoExecute.enabled")
										: t("autoRefactor:config.autoExecute.disabled")}
								</Label>
							</div>
							{autoExecute && (
								<p className="text-xs text-destructive">
									{t("autoRefactor:config.autoExecute.warning")}
								</p>
							)}
						</div>

						{/* Model Selection */}
						<div className="space-y-2">
							<Label htmlFor="model-select">
								{t("autoRefactor:config.model.label")}
							</Label>
							<Select
								value={model}
								onValueChange={(value) => setModel(value)}
								disabled={isAnalyzing || isExecuting}
							>
								<SelectTrigger id="model-select">
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{MODELS.map((modelOption) => (
										<SelectItem key={modelOption} value={modelOption}>
											{modelOption}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>

						{/* Thinking Level */}
						<div className="space-y-2">
							<Label htmlFor="thinking-level">
								{t("autoRefactor:config.thinkingLevel.label")}
							</Label>
							<Select
								value={thinkingLevel}
								onValueChange={(value) => setThinkingLevel(value)}
								disabled={isAnalyzing || isExecuting}
							>
								<SelectTrigger id="thinking-level">
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{THINKING_LEVELS.map((level) => (
										<SelectItem key={level} value={level}>
											{t(`autoRefactor:config.thinkingLevel.options.${level}`)}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
					</div>

					{/* No Project Warning */}
					{!selectedProjectId && (
						<div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
							<p className="text-sm text-destructive">
								{t("autoRefactor:errors.noProject")}
							</p>
						</div>
					)}

					{/* Status / Streaming Output during analysis */}
					{(isAnalyzing || isExecuting) && (
						<div className="space-y-3">
							<div className="flex items-center gap-2 text-sm text-muted-foreground">
								<Loader2 className="h-4 w-4 animate-spin text-primary" />
								<span>{status || t("autoRefactor:status.analyzing")}</span>
							</div>
							{streamingOutput && (
								<div className="space-y-1">
									<Label className="text-xs text-muted-foreground">
										{t("autoRefactor:result.streamingOutput")}
									</Label>
									<pre
										ref={streamOutputRef}
										className="bg-muted/50 rounded-lg p-3 text-xs font-mono max-h-[200px] overflow-y-auto whitespace-pre-wrap wrap-break-word"
									>
										{streamingOutput}
									</pre>
								</div>
							)}
						</div>
					)}

					{/* Error state */}
					{isError && (
						<div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 space-y-2">
							<p className="text-sm font-medium text-destructive">
								{t("autoRefactor:status.error")}
							</p>
							<p className="text-sm text-destructive/80">
								{error || t("autoRefactor:errors.generic")}
							</p>
						</div>
					)}

					{/* Result */}
					{isComplete && result && (
						<ResultView
							result={result}
							executionResult={executionResult}
							copied={copied}
							onCopy={handleCopy}
							t={t}
						/>
					)}
				</div>

				{/* Footer Buttons */}
				<DialogFooter className="gap-2 sm:gap-0">
					{/* Idle / Input state */}
					{phase === "idle" && (
						<>
							<Button variant="outline" onClick={handleClose}>
								{t("autoRefactor:actions.close")}
							</Button>
							<Button
								onClick={handleStart}
								disabled={!canStart}
								className="gap-2"
							>
								<RefreshCw className="h-4 w-4" />
								{autoExecute
									? t("autoRefactor:actions.execute")
									: t("autoRefactor:actions.analyze")}
							</Button>
						</>
					)}

					{/* Analyzing / Executing state */}
					{(isAnalyzing || isExecuting) && (
						<>
							<Button variant="outline" onClick={handleCancel}>
								{t("autoRefactor:actions.cancel")}
							</Button>
							<Button variant="outline" onClick={handleClose}>
								{t("autoRefactor:actions.close")}
							</Button>
						</>
					)}

					{/* Error state */}
					{isError && (
						<>
							<Button variant="outline" onClick={handleClose}>
								{t("autoRefactor:actions.close")}
							</Button>
							<Button onClick={handleTryAgain} className="gap-2">
								<RefreshCw className="h-4 w-4" />
								{t("autoRefactor:actions.tryAgain")}
							</Button>
						</>
					)}

					{/* Complete state */}
					{isComplete && (
						<Button variant="outline" onClick={handleClose}>
							{t("autoRefactor:actions.close")}
						</Button>
					)}
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

/**
 * Renders the analysis result with summary, issues, and refactoring plan
 */
function ResultView({
	result,
	executionResult,
	copied,
	onCopy,
	t,
}: {
	result: AutoRefactorResult;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	executionResult: any | null;
	copied: boolean;
	onCopy: (text: string) => void;
	t: (key: string) => string;
}) {
	const { summary } = result;

	return (
		<div className="space-y-6">
			{/* Summary Cards */}
			<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
				<SummaryCard
					icon={<AlertTriangle className="h-4 w-4" />}
					title={t("autoRefactor:summary.issuesFound")}
					value={summary.issues_found.toString()}
					color="text-orange-600"
				/>
				<SummaryCard
					icon={<TrendingUp className="h-4 w-4" />}
					title={t("autoRefactor:summary.refactoringItems")}
					value={summary.refactoring_items.toString()}
					color="text-blue-600"
				/>
				<SummaryCard
					icon={<Zap className="h-4 w-4" />}
					title={t("autoRefactor:summary.quickWins")}
					value={summary.quick_wins.toString()}
					color="text-green-600"
				/>
				<SummaryCard
					icon={<Shield className="h-4 w-4" />}
					title={t("autoRefactor:summary.riskLevel")}
					value={summary.risk_level}
					color="text-purple-600"
				/>
			</div>

			{/* Detailed Analysis */}
			<div className="space-y-4">
				{/* Analysis Details */}
				<div className="space-y-2">
					<div className="flex items-center justify-between">
						<Label className="text-sm font-medium">
							{t("autoRefactor:result.analysis.title")}
						</Label>
						<Button
							variant="ghost"
							size="sm"
							onClick={() => onCopy(JSON.stringify(result.analysis, null, 2))}
							className="h-7 gap-1.5 text-xs"
						>
							{copied ? (
								<>
									<Check className="h-3 w-3" />
									{t("autoRefactor:actions.copied")}
								</>
							) : (
								<>
									<Copy className="h-3 w-3" />
									{t("autoRefactor:actions.copy")}
								</>
							)}
						</Button>
					</div>
					<div className="bg-muted/50 rounded-lg p-3 max-h-[200px] overflow-y-auto">
						<pre className="text-xs text-muted-foreground whitespace-pre-wrap">
							{JSON.stringify(result.analysis, null, 2)}
						</pre>
					</div>
				</div>

				{/* Refactoring Plan */}
				<div className="space-y-2">
					<div className="flex items-center justify-between">
						<Label className="text-sm font-medium">
							{t("autoRefactor:result.plan.title")}
						</Label>
						<Button
							variant="ghost"
							size="sm"
							onClick={() => onCopy(JSON.stringify(result.plan, null, 2))}
							className="h-7 gap-1.5 text-xs"
						>
							{copied ? (
								<>
									<Check className="h-3 w-3" />
									{t("autoRefactor:actions.copied")}
								</>
							) : (
								<>
									<Copy className="h-3 w-3" />
									{t("autoRefactor:actions.copy")}
								</>
							)}
						</Button>
					</div>
					<div className="bg-muted/50 rounded-lg p-3 max-h-[200px] overflow-y-auto">
						<pre className="text-xs text-muted-foreground whitespace-pre-wrap">
							{JSON.stringify(result.plan, null, 2)}
						</pre>
					</div>
				</div>

				{/* Execution Result (if available) */}
				{executionResult && (
					<div className="space-y-2">
						<div className="flex items-center justify-between">
							<Label className="text-sm font-medium">
								{t("autoRefactor:result.execution.title")}
							</Label>
							<Button
								variant="ghost"
								size="sm"
								onClick={() => onCopy(JSON.stringify(executionResult, null, 2))}
								className="h-7 gap-1.5 text-xs"
							>
								{copied ? (
									<>
										<Check className="h-3 w-3" />
										{t("autoRefactor:actions.copied")}
									</>
								) : (
									<>
										<Copy className="h-3 w-3" />
										{t("autoRefactor:actions.copy")}
									</>
								)}
							</Button>
						</div>
						<div className="bg-muted/50 rounded-lg p-3 max-h-[200px] overflow-y-auto">
							<pre className="text-xs text-muted-foreground whitespace-pre-wrap">
								{JSON.stringify(executionResult, null, 2)}
							</pre>
						</div>
					</div>
				)}
			</div>
		</div>
	);
}

/**
 * Summary card component
 */
function SummaryCard({
	icon,
	title,
	value,
	color,
}: {
	icon: React.ReactNode;
	title: string;
	value: string;
	color: string;
}) {
	return (
		<div className="bg-card border rounded-lg p-3 space-y-2">
			<div className={`flex items-center gap-2 ${color}`}>
				{icon}
				<span className="text-xs font-medium">{title}</span>
			</div>
			<div className="text-lg font-bold">{value}</div>
		</div>
	);
}

export default AutoRefactorDialog;
