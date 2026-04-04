import {
	AlertCircle,
	CheckCircle2,
	ChevronDown,
	ChevronRight,
	Clock,
	FileText,
	FlaskConical,
	Loader2,
	MinusCircle,
	Play,
	XCircle,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useBrowserAgentStore } from "@/stores/browser-agent-store";

interface TestRunnerTabProps {
	readonly projectPath: string;
}

export function TestRunnerTab({ projectPath }: TestRunnerTabProps) {
	const { t } = useTranslation(["browserAgent"]);
	const { recentTestRun, isRunningTests, runTests } = useBrowserAgentStore();
	const [expandedTest, setExpandedTest] = useState<string | null>(null);

	const handleRunTests = () => {
		runTests(projectPath);
	};

	return (
		<div className="flex flex-col gap-4">
			{/* Header with run button and summary */}
			<div className="flex items-center justify-between">
				<button
					type="button"
					onClick={handleRunTests}
					disabled={isRunningTests}
					className="px-4 py-2 rounded-lg bg-emerald-500 text-white text-sm font-medium hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors shadow-sm shadow-emerald-500/20"
				>
					{isRunningTests ? (
						<Loader2 className="w-4 h-4 animate-spin" />
					) : (
						<Play className="w-4 h-4" />
					)}
					{isRunningTests
						? t("browserAgent:tests.running")
						: t("browserAgent:tests.runAll")}
				</button>

				{/* Summary badges */}
				{recentTestRun && (
					<div className="flex items-center gap-2">
						<SummaryBadge
							icon={CheckCircle2}
							count={recentTestRun.passed}
							color="emerald"
							label={t("browserAgent:tests.passed")}
						/>
						<SummaryBadge
							icon={XCircle}
							count={recentTestRun.failed}
							color="rose"
							label={t("browserAgent:tests.failed")}
						/>
						<SummaryBadge
							icon={MinusCircle}
							count={recentTestRun.skipped}
							color="amber"
							label={t("browserAgent:tests.skipped")}
						/>
						<div className="flex items-center gap-1 text-xs text-blue-400/80 bg-blue-500/10 px-2 py-1 rounded-md border border-blue-500/15">
							<Clock className="w-3 h-3" />
							<span className="font-mono">
								{(recentTestRun.durationMs / 1000).toFixed(1)}s
							</span>
						</div>
					</div>
				)}
			</div>

			{/* Progress bar during test run */}
			{isRunningTests && (
				<div className="w-full h-1.5 rounded-full bg-emerald-500/10 overflow-hidden">
					<div
						className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full animate-pulse"
						style={{ width: "60%" }}
					/>
				</div>
			)}

			{/* Empty state */}
			{!recentTestRun && !isRunningTests && (
				<div className="flex flex-col items-center justify-center h-56 gap-4">
					<div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-500/15 to-teal-500/15 border border-emerald-500/20 flex items-center justify-center shadow-lg shadow-emerald-500/5">
						<FlaskConical className="w-10 h-10 text-emerald-400/70" />
					</div>
					<div className="text-center max-w-xs">
						<p className="text-sm font-medium text-[var(--text-secondary)] mb-1">
							{t("browserAgent:tests.noResultsTitle")}
						</p>
						<p className="text-xs text-[var(--text-tertiary)] leading-relaxed">
							{t("browserAgent:tests.noResults")}
						</p>
					</div>
				</div>
			)}

			{/* Test results */}
			{recentTestRun && (
				<div className="rounded-lg border border-[var(--border-primary)] overflow-hidden">
					{recentTestRun.results.map((result, index) => {
						const key = `${result.path}:${result.name}`;
						const isExpanded = expandedTest === key;
						const {
							icon: StatusIcon,
							color,
							bgColor,
							borderColor,
						} = getStatusConfig(result.status);
						const isLast = index === recentTestRun.results.length - 1;

						return (
							<div key={key}>
								<button
									type="button"
									onClick={() => setExpandedTest(isExpanded ? null : key)}
									className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--bg-hover)] text-left transition-colors ${
										!isLast || isExpanded
											? "border-b border-[var(--border-primary)]"
											: ""
									} ${isExpanded ? "bg-[var(--bg-secondary)]" : ""}`}
								>
									{/* Status icon */}
									<StatusIcon className={`w-4 h-4 ${color} shrink-0`} />

									{/* Test info */}
									<div className="flex-1 min-w-0 flex items-center gap-2">
										<span className="text-sm text-[var(--text-primary)] truncate">
											{result.name}
										</span>
										<span className="text-[11px] text-[var(--text-tertiary)] truncate flex items-center gap-1">
											<FileText className="w-3 h-3 shrink-0 text-indigo-400/50" />
											{result.path}
										</span>
									</div>

									{/* Duration + expand */}
									<div className="flex items-center gap-2 shrink-0">
										<span className="text-[11px] text-blue-400/60 font-mono">
											{result.durationMs.toFixed(0)}ms
										</span>
										{result.errorMessage &&
											(isExpanded ? (
												<ChevronDown className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />
											) : (
												<ChevronRight className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />
											))}
									</div>
								</button>

								{/* Error details */}
								{isExpanded && result.errorMessage && (
									<div
										className={`px-4 py-3 ${bgColor} border-b ${borderColor}`}
									>
										<p className="text-xs font-medium text-rose-400 mb-1.5 flex items-center gap-1.5">
											<AlertCircle className="w-3 h-3" />
											{t("browserAgent:tests.errorDetails")}
										</p>
										<pre className="text-xs text-[var(--text-secondary)] whitespace-pre-wrap font-mono leading-relaxed bg-black/20 rounded-md p-3 border border-rose-500/10">
											{result.errorMessage}
										</pre>
									</div>
								)}
							</div>
						);
					})}
				</div>
			)}
		</div>
	);
}

// ── Status config ───────────────────────────────────────────

function getStatusConfig(status: string): {
	icon: typeof CheckCircle2;
	color: string;
	bgColor: string;
	borderColor: string;
} {
	switch (status) {
		case "passed":
			return {
				icon: CheckCircle2,
				color: "text-emerald-400",
				bgColor: "bg-emerald-500/5",
				borderColor: "border-emerald-500/15",
			};
		case "failed":
			return {
				icon: XCircle,
				color: "text-rose-400",
				bgColor: "bg-rose-500/5",
				borderColor: "border-rose-500/15",
			};
		case "skipped":
			return {
				icon: MinusCircle,
				color: "text-amber-400",
				bgColor: "bg-amber-500/5",
				borderColor: "border-amber-500/15",
			};
		case "error":
			return {
				icon: AlertCircle,
				color: "text-red-500",
				bgColor: "bg-red-500/5",
				borderColor: "border-red-500/15",
			};
		default:
			return {
				icon: AlertCircle,
				color: "text-[var(--text-tertiary)]",
				bgColor: "bg-[var(--bg-secondary)]",
				borderColor: "border-[var(--border-primary)]",
			};
	}
}

// ── Summary Badge ───────────────────────────────────────────

function SummaryBadge({
	icon: Icon,
	count,
	color,
	label,
}: {
	readonly icon: typeof CheckCircle2;
	readonly count: number;
	readonly color: "emerald" | "rose" | "amber";
	readonly label: string;
}) {
	const colorClasses = {
		emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
		rose: "text-rose-400 bg-rose-500/10 border-rose-500/20",
		amber: "text-amber-400 bg-amber-500/10 border-amber-500/20",
	};

	return (
		<div
			className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium border ${colorClasses[color]}`}
			title={label}
		>
			<Icon className="w-3 h-3" />
			<span>{count}</span>
		</div>
	);
}
