import {
	Activity,
	AlertTriangle,
	Brain,
	Check,
	ChevronDown,
	ChevronRight,
	Loader2,
	RefreshCw,
	ToggleLeft,
	ToggleRight,
	Trash2,
	TrendingDown,
	TrendingUp,
	X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { LearningPattern } from "../../../shared/types/learning-loop";
import {
	cancelLearningAnalysis,
	deleteLearningPattern,
	loadLearningPatterns,
	loadLearningSummary,
	setupLearningLoopListeners,
	startLearningAnalysis,
	toggleLearningPattern,
	useLearningLoopStore,
} from "../../stores/learning-loop-store";
import { useProjectStore } from "../../stores/project-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "../ui/dialog";
import { ScrollArea } from "../ui/scroll-area";

const CATEGORY_COLORS: Record<string, string> = {
	tool_sequence: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
	prompt_strategy: "bg-purple-500/10 text-purple-700 dark:text-purple-400",
	error_resolution: "bg-red-500/10 text-red-700 dark:text-red-400",
	qa_pattern: "bg-green-500/10 text-green-700 dark:text-green-400",
	code_structure: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
};

const TYPE_ICONS: Record<string, React.ElementType> = {
	success: TrendingUp,
	failure: TrendingDown,
	optimization: Activity,
};

/**
 * LearningLoopDialog — Autonomous Agent Learning Loop dashboard.
 *
 * Shows patterns extracted from past builds, lets users run analysis,
 * and manage (enable/disable/delete) individual patterns.
 */
export function LearningLoopDialog() {
	const { t } = useTranslation(["learningLoop", "common"]);
	const streamOutputRef = useRef<HTMLPreElement>(null);
	const [expandedPatterns, setExpandedPatterns] = useState<Set<string>>(
		new Set(),
	);

	const {
		isOpen,
		closeDialog,
		phase,
		status,
		streamingOutput,
		patterns,
		summary,
		error,
		isLoading,
	} = useLearningLoopStore();

	const selectedProjectId = useProjectStore((s) => s.selectedProjectId);
	const selectedProject = useProjectStore((s) =>
		s.projects.find((p) => p.id === s.selectedProjectId),
	);

	// Setup IPC listeners once
	useEffect(() => {
		const cleanup = setupLearningLoopListeners();
		return cleanup;
	}, []);

	// Load data when dialog opens
	useEffect(() => {
		if (isOpen && selectedProject?.path) {
			loadLearningPatterns(selectedProject.path);
			loadLearningSummary(selectedProject.path);
		}
	}, [isOpen, selectedProject?.path]);

	// Auto-scroll streaming output
	useEffect(() => {
		if (streamOutputRef.current) {
			streamOutputRef.current.scrollTop = streamOutputRef.current.scrollHeight;
		}
	}, []);

	const handleStartAnalysis = useCallback(() => {
		if (!selectedProject?.path) return;
		startLearningAnalysis(selectedProject.path);
	}, [selectedProject?.path]);

	const handleCancel = useCallback(() => {
		cancelLearningAnalysis();
	}, []);

	const handleClose = useCallback(() => {
		if (phase === "analyzing") {
			handleCancel();
		}
		closeDialog();
	}, [phase, closeDialog, handleCancel]);

	const handleTogglePattern = useCallback(
		async (patternId: string) => {
			if (!selectedProject?.path) return;
			await toggleLearningPattern(selectedProject.path, patternId);
		},
		[selectedProject?.path],
	);

	const handleDeletePattern = useCallback(
		async (patternId: string) => {
			if (!selectedProject?.path) return;
			await deleteLearningPattern(selectedProject.path, patternId);
		},
		[selectedProject?.path],
	);

	const toggleExpanded = useCallback((patternId: string) => {
		setExpandedPatterns((prev) => {
			const next = new Set(prev);
			if (next.has(patternId)) {
				next.delete(patternId);
			} else {
				next.add(patternId);
			}
			return next;
		});
	}, []);

	const isAnalyzing = phase === "analyzing";
	const isComplete = phase === "complete";
	const isError = phase === "error";
	const canStart = selectedProjectId && !isAnalyzing;

	const confidenceColor = (confidence: number) => {
		if (confidence >= 0.8) return "text-green-600 dark:text-green-400";
		if (confidence >= 0.6) return "text-amber-600 dark:text-amber-400";
		return "text-red-600 dark:text-red-400";
	};

	return (
		<Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
			<DialogContent className="sm:max-w-[900px] max-h-[90vh] flex flex-col">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<Brain className="h-5 w-5 text-primary" />
						{t("learningLoop:title")}
					</DialogTitle>
					<DialogDescription>{t("learningLoop:description")}</DialogDescription>
				</DialogHeader>

				<div className="flex-1 overflow-y-auto space-y-4 py-2">
					{/* Summary Cards */}
					{summary && summary.total_patterns > 0 && (
						<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
							<div className="bg-muted/50 rounded-lg p-3 text-center">
								<div className="text-2xl font-bold">
									{summary.total_patterns}
								</div>
								<div className="text-xs text-muted-foreground">
									{t("learningLoop:summary.totalPatterns")}
								</div>
							</div>
							<div className="bg-muted/50 rounded-lg p-3 text-center">
								<div className="text-2xl font-bold">
									{summary.enabled_count}
								</div>
								<div className="text-xs text-muted-foreground">
									{t("learningLoop:summary.enabled")}
								</div>
							</div>
							<div className="bg-muted/50 rounded-lg p-3 text-center">
								<div className="text-2xl font-bold">
									{(summary.average_confidence * 100).toFixed(0)}%
								</div>
								<div className="text-xs text-muted-foreground">
									{t("learningLoop:summary.avgConfidence")}
								</div>
							</div>
							<div className="bg-muted/50 rounded-lg p-3 text-center">
								<div className="text-2xl font-bold">
									{summary.total_builds_analyzed}
								</div>
								<div className="text-xs text-muted-foreground">
									{t("learningLoop:summary.buildsAnalyzed")}
								</div>
							</div>
						</div>
					)}

					{/* No Project Warning */}
					{!selectedProjectId && (
						<div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
							<p className="text-sm text-destructive">
								{t("learningLoop:errors.noProject")}
							</p>
						</div>
					)}

					{/* Error display */}
					{isError && error && (
						<div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3 flex items-start gap-2">
							<AlertTriangle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
							<p className="text-sm text-destructive">{error}</p>
						</div>
					)}

					{/* Analyzing state */}
					{isAnalyzing && (
						<div className="space-y-3">
							<div className="flex items-center gap-2 text-sm text-muted-foreground">
								<Loader2 className="h-4 w-4 animate-spin text-primary" />
								<span>{status || t("learningLoop:status.analyzing")}</span>
							</div>
							{streamingOutput && (
								<pre
									ref={streamOutputRef}
									className="bg-muted/50 rounded-lg p-3 text-xs font-mono max-h-[200px] overflow-y-auto whitespace-pre-wrap wrap-break-words"
								>
									{streamingOutput}
								</pre>
							)}
						</div>
					)}

					{/* Complete state */}
					{isComplete && (
						<div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
							<Check className="h-4 w-4" />
							<span>{t("learningLoop:status.complete")}</span>
						</div>
					)}

					{/* Patterns List */}
					{!isAnalyzing && patterns.length > 0 && (
						<div className="space-y-2">
							<h3 className="text-sm font-medium">
								{t("learningLoop:patterns.title", { count: patterns.length })}
							</h3>
							<ScrollArea className="max-h-[400px]">
								<div className="space-y-2 pr-3">
									{patterns.map((pattern) => (
										<PatternCard
											key={pattern.pattern_id}
											pattern={pattern}
											isExpanded={expandedPatterns.has(pattern.pattern_id)}
											onToggleExpand={() => toggleExpanded(pattern.pattern_id)}
											onToggleEnabled={() =>
												handleTogglePattern(pattern.pattern_id)
											}
											onDelete={() => handleDeletePattern(pattern.pattern_id)}
											confidenceColor={confidenceColor}
											t={t}
										/>
									))}
								</div>
							</ScrollArea>
						</div>
					)}

					{/* Empty state */}
					{!isAnalyzing && !isLoading && patterns.length === 0 && !isError && (
						<div className="text-center py-8 text-muted-foreground">
							<Brain className="h-12 w-12 mx-auto mb-3 opacity-30" />
							<p className="text-sm">{t("learningLoop:empty.title")}</p>
							<p className="text-xs mt-1">
								{t("learningLoop:empty.description")}
							</p>
						</div>
					)}

					{/* Loading state */}
					{isLoading && (
						<div className="flex items-center justify-center py-8">
							<Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
						</div>
					)}
				</div>

				<DialogFooter className="flex justify-between sm:justify-between">
					<Button variant="outline" onClick={handleClose}>
						{t("common:actions.close")}
					</Button>
					<div className="flex gap-2">
						{isAnalyzing && (
							<Button variant="destructive" onClick={handleCancel}>
								<X className="h-4 w-4 mr-1" />
								{t("common:actions.cancel")}
							</Button>
						)}
						{!isAnalyzing && (
							<Button onClick={handleStartAnalysis} disabled={!canStart}>
								<RefreshCw className="h-4 w-4 mr-1" />
								{patterns.length > 0
									? t("learningLoop:actions.reanalyze")
									: t("learningLoop:actions.analyze")}
							</Button>
						)}
					</div>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

/**
 * Individual pattern card component
 */
interface PatternCardProps {
	readonly pattern: LearningPattern;
	readonly isExpanded: boolean;
	readonly onToggleExpand: () => void;
	readonly onToggleEnabled: () => void;
	readonly onDelete: () => void;
	readonly confidenceColor: (c: number) => string;
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	readonly t: (key: string, options?: any) => string;
}

function PatternCard({
	pattern,
	isExpanded,
	onToggleExpand,
	onToggleEnabled,
	onDelete,
	confidenceColor,
	t,
}: PatternCardProps) {
	const TypeIcon = TYPE_ICONS[pattern.pattern_type] || Activity;
	const categoryClass =
		CATEGORY_COLORS[pattern.category] || "bg-gray-500/10 text-gray-700";

	return (
		<div
			className={`border rounded-lg p-3 transition-colors ${
				pattern.enabled ? "border-border" : "border-border/50 opacity-60"
			}`}
		>
			{/* Header row */}
			<div className="flex items-start gap-2">
				<button
					type="button"
					onClick={onToggleExpand}
					className="mt-0.5 text-muted-foreground hover:text-foreground transition-colors"
				>
					{isExpanded ? (
						<ChevronDown className="h-4 w-4" />
					) : (
						<ChevronRight className="h-4 w-4" />
					)}
				</button>

				<TypeIcon className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />

				<div className="flex-1 min-w-0">
					<p className="text-sm font-medium leading-tight truncate">
						{pattern.description}
					</p>
					<div className="flex items-center gap-2 mt-1 flex-wrap">
						<Badge
							variant="secondary"
							className={`text-[10px] px-1.5 py-0 ${categoryClass}`}
						>
							{t(`learningLoop:categories.${pattern.category}`)}
						</Badge>
						<Badge variant="outline" className="text-[10px] px-1.5 py-0">
							{pattern.agent_phase}
						</Badge>
						<span
							className={`text-[10px] font-mono ${confidenceColor(pattern.confidence)}`}
						>
							{(pattern.confidence * 100).toFixed(0)}%
						</span>
						{pattern.occurrence_count > 1 && (
							<span className="text-[10px] text-muted-foreground">
								×{pattern.occurrence_count}
							</span>
						)}
					</div>
				</div>

				{/* Actions */}
				<div className="flex items-center gap-1 shrink-0">
					<button
						type="button"
						onClick={onToggleEnabled}
						className="p-1 text-muted-foreground hover:text-foreground transition-colors"
						title={
							pattern.enabled
								? t("learningLoop:actions.disable")
								: t("learningLoop:actions.enable")
						}
					>
						{pattern.enabled ? (
							<ToggleRight className="h-4 w-4 text-green-600 dark:text-green-400" />
						) : (
							<ToggleLeft className="h-4 w-4" />
						)}
					</button>
					<button
						type="button"
						onClick={onDelete}
						className="p-1 text-muted-foreground hover:text-destructive transition-colors"
						title={t("learningLoop:actions.delete")}
					>
						<Trash2 className="h-3.5 w-3.5" />
					</button>
				</div>
			</div>

			{/* Expanded details */}
			{isExpanded && (
				<div className="mt-3 ml-6 space-y-2 text-xs">
					<div className="bg-muted/50 rounded p-2">
						<p className="font-medium text-muted-foreground mb-1">
							{t("learningLoop:patterns.instruction")}
						</p>
						<p className="text-foreground whitespace-pre-wrap">
							{pattern.actionable_instruction}
						</p>
					</div>
					<div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground">
						<span>
							{t("learningLoop:patterns.applied", {
								count: pattern.applied_count,
							})}
						</span>
						{pattern.applied_count > 0 && (
							<span>
								{t("learningLoop:patterns.effectiveness", {
									rate: (pattern.effectiveness_rate * 100).toFixed(0),
								})}
							</span>
						)}
						<span>
							{t("learningLoop:patterns.source")}: {pattern.source}
						</span>
					</div>
					{pattern.context_tags.length > 0 && (
						<div className="flex flex-wrap gap-1">
							{pattern.context_tags.map((tag) => (
								<Badge
									key={tag}
									variant="outline"
									className="text-[10px] px-1 py-0"
								>
									{tag}
								</Badge>
							))}
						</div>
					)}
				</div>
			)}
		</div>
	);
}
