import type React from "react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
	setupAccessibilityListeners,
	useAccessibilityStore,
	type WcagTargetLevel,
} from "../../stores/accessibility-store";
import type {
	A11yReport,
	A11ySeverity,
} from "../../../shared/types/accessibility";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";

const SEVERITY_STYLES: Record<A11ySeverity, string> = {
	critical: "text-red-400 bg-red-500/10 border-red-500/20",
	serious: "text-orange-400 bg-orange-500/10 border-orange-500/20",
	moderate: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	minor: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

type FilterType = "all" | "critical" | "serious" | "passed";

interface A11yReportViewProps {
	readonly projectPath?: string;
}

export function A11yReportView({
	projectPath,
}: A11yReportViewProps): React.ReactElement {
	const { t } = useTranslation("accessibility");

	useEffect(() => {
		const cleanup = setupAccessibilityListeners();
		return cleanup;
	}, []);

	const phase = useAccessibilityStore((s) => s.phase);
	const status = useAccessibilityStore((s) => s.status);
	const report = useAccessibilityStore((s) => s.report);
	const error = useAccessibilityStore((s) => s.error);
	const targetLevel = useAccessibilityStore((s) => s.targetLevel);
	const setTargetLevel = useAccessibilityStore((s) => s.setTargetLevel);
	const startScan = useAccessibilityStore((s) => s.startScan);
	const cancelScan = useAccessibilityStore((s) => s.cancelScan);
	const reset = useAccessibilityStore((s) => s.reset);

	const isScanning = phase === "scanning";
	const canRun = !!projectPath && !isScanning;

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<Toolbar
				targetLevel={targetLevel}
				onTargetLevelChange={setTargetLevel}
				disabled={isScanning}
				canRun={canRun}
				isScanning={isScanning}
				hasReport={!!report}
				onRun={() => projectPath && startScan(projectPath)}
				onCancel={() => cancelScan()}
				onReset={reset}
				t={t}
			/>

			{!projectPath && (
				<div className="text-sm text-(--text-secondary)">
					{t("errors.noProject")}
				</div>
			)}

			{isScanning && (
				<div className="text-sm text-(--text-secondary) animate-pulse">
					{status || t("actions.scanning")}
				</div>
			)}

			{phase === "error" && error && (
				<div className="text-sm text-red-400">
					{t("errors.failed", { error })}
				</div>
			)}

			{report ? (
				<div className="flex-1 min-h-0">
					<ReportBody report={report} t={t} />
				</div>
			) : (
				phase === "idle" && (
					<div className="flex items-center justify-center h-40 text-(--text-secondary)">
						<p>{t("noData")}</p>
					</div>
				)
			)}
		</div>
	);
}

function Toolbar({
	targetLevel,
	onTargetLevelChange,
	disabled,
	canRun,
	isScanning,
	hasReport,
	onRun,
	onCancel,
	onReset,
	t,
}: {
	readonly targetLevel: WcagTargetLevel;
	readonly onTargetLevelChange: (level: WcagTargetLevel) => void;
	readonly disabled: boolean;
	readonly canRun: boolean;
	readonly isScanning: boolean;
	readonly hasReport: boolean;
	readonly onRun: () => void;
	readonly onCancel: () => void;
	readonly onReset: () => void;
	readonly t: (key: string) => string;
}): React.ReactElement {
	return (
		<div className="flex items-center gap-3 flex-wrap">
			<div className="flex items-center gap-2">
				<span className="text-sm text-(--text-secondary)">{t("levels.label")}</span>
				<Select
					value={targetLevel}
					disabled={disabled}
					onValueChange={(value) => onTargetLevelChange(value as WcagTargetLevel)}
				>
					<SelectTrigger className="w-24">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						<SelectItem value="A">A</SelectItem>
						<SelectItem value="AA">AA</SelectItem>
						<SelectItem value="AAA">AAA</SelectItem>
					</SelectContent>
				</Select>
			</div>

			{isScanning ? (
				<button
					type="button"
					onClick={onCancel}
					className="px-3 py-1.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-sm hover:bg-red-500/20"
				>
					{t("actions.cancel")}
				</button>
			) : (
				<button
					type="button"
					onClick={onRun}
					disabled={!canRun}
					className="px-3 py-1.5 rounded bg-(--accent-color) text-white text-sm disabled:opacity-50"
				>
					{t("actions.runScan")}
				</button>
			)}

			{hasReport && !isScanning && (
				<button
					type="button"
					onClick={onReset}
					className="px-3 py-1.5 rounded bg-(--bg-secondary) border border-(--border-color) text-sm hover:bg-(--bg-tertiary)"
				>
					{t("actions.reset")}
				</button>
			)}
		</div>
	);
}

function ReportBody({
	report,
	t,
}: {
	readonly report: A11yReport;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
}): React.ReactElement {
	const [filter, setFilter] = useState<FilterType>("all");
	const [searchQuery, setSearchQuery] = useState("");

	const criticalCount = report.violations.filter(
		(v) => v.severity === "critical",
	).length;
	const seriousCount = report.violations.filter(
		(v) => v.severity === "serious",
	).length;

	const filteredViolations = report.violations.filter((v) => {
		const matchesFilter =
			filter === "all" ||
			(filter === "critical" && v.severity === "critical") ||
			(filter === "serious" && v.severity === "serious");

		const matchesSearch =
			searchQuery === "" ||
			v.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
			v.ruleId.toLowerCase().includes(searchQuery.toLowerCase()) ||
			v.file.toLowerCase().includes(searchQuery.toLowerCase());

		return matchesFilter && matchesSearch;
	});

	const filteredPassedRules = report.passedRules.filter((rule) =>
		searchQuery === "" || rule.toLowerCase().includes(searchQuery.toLowerCase()),
	);

	return (
		<div className="flex flex-col flex-1 gap-4">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{t("targetInfo", {
						targetLevel: report.targetLevel,
						filesScanned: report.filesScanned,
					})}
				</p>
			</div>

			<div>
				<input
					type="text"
					placeholder={t("search.placeholder")}
					value={searchQuery}
					onChange={(e) => setSearchQuery(e.target.value)}
					className="w-full px-3 py-2 rounded-lg bg-(--bg-secondary) border border-(--border-color) text-(--text-primary) placeholder:text-(--text-secondary) focus:outline-none focus:ring-2 focus:ring-(--accent-color)"
				/>
			</div>

			<div className="grid grid-cols-4 gap-3">
				<StatCard
					label={t("stats.violations")}
					value={report.violations.length}
					color="text-red-400"
					isActive={filter === "all"}
					onClick={() => setFilter("all")}
				/>
				<StatCard
					label={t("stats.critical")}
					value={criticalCount}
					color="text-red-400"
					isActive={filter === "critical"}
					onClick={() => setFilter("critical")}
				/>
				<StatCard
					label={t("stats.serious")}
					value={seriousCount}
					color="text-orange-400"
					isActive={filter === "serious"}
					onClick={() => setFilter("serious")}
				/>
				<StatCard
					label={t("stats.rulesPassed")}
					value={report.passedRules.length}
					color="text-green-400"
					isActive={filter === "passed"}
					onClick={() => setFilter("passed")}
				/>
			</div>

			<div className="space-y-2">
				{filter === "passed" ? (
					<div className="space-y-2">
						{filteredPassedRules.map((rule, idx) => (
							<div
								key={`passed-${rule}-${idx}`}
								className="px-4 py-3 rounded-lg border border-green-500/20 bg-green-500/10 text-green-400"
							>
								<p className="text-sm">{rule}</p>
							</div>
						))}
					</div>
				) : (
					filteredViolations.map((v, idx) => (
						<div
							key={`${v.ruleId}-${v.file}-${v.line}-${idx}`}
							className={`px-4 py-3 rounded-lg border ${SEVERITY_STYLES[v.severity]}`}
						>
							<div className="flex items-center gap-2 mb-1">
								<span className="text-xs font-medium uppercase">{v.severity}</span>
								<span className="text-xs opacity-70">
									{v.ruleId} · {v.wcagCriteria}
								</span>
							</div>
							<p className="text-sm">{v.description}</p>
							<p className="text-xs mt-1 opacity-70 font-mono">
								{v.file}:{v.line}
							</p>
							{v.suggestion && (
								<p className="text-xs mt-1 text-green-400">{v.suggestion}</p>
							)}
						</div>
					))
				)}
			</div>

			{report.summary && (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{report.summary}
				</p>
			)}
		</div>
	);
}

function StatCard({
	label,
	value,
	color,
	isActive = false,
	onClick,
}: {
	readonly label: string;
	readonly value: number;
	readonly color: string;
	readonly isActive?: boolean;
	readonly onClick?: () => void;
}): React.ReactElement {
	return (
		<button
			type="button"
			className={`p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color) cursor-pointer transition-colors hover:bg-(--bg-tertiary) text-left ${
				isActive ? "ring-2 ring-(--accent-color)" : ""
			}`}
			onClick={onClick}
		>
			<p className="text-xs text-(--text-secondary)">{label}</p>
			<p className={`text-2xl font-bold ${color}`}>{value}</p>
		</button>
	);
}
