import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupApiWatcherListeners,
	useApiWatcherStore,
} from "../../stores/api-watcher-store";
import type {
	ContractChange,
	ContractDiff,
} from "../../../shared/types/api-watcher";

const CATEGORY_STYLES: Record<string, { color: string; icon: string }> = {
	breaking: { color: "text-red-400 bg-red-500/10", icon: "🔴" },
	potentially_breaking: {
		color: "text-yellow-400 bg-yellow-500/10",
		icon: "🟡",
	},
	non_breaking: { color: "text-green-400 bg-green-500/10", icon: "🟢" },
};

interface ApiWatcherDashboardProps {
	readonly projectPath?: string;
}

export function ApiWatcherDashboard({
	projectPath,
}: ApiWatcherDashboardProps): React.ReactElement {
	const { t } = useTranslation("apiWatcher");

	useEffect(() => {
		const cleanup = setupApiWatcherListeners();
		return cleanup;
	}, []);

	const phase = useApiWatcherStore((s) => s.phase);
	const status = useApiWatcherStore((s) => s.status);
	const result = useApiWatcherStore((s) => s.result);
	const error = useApiWatcherStore((s) => s.error);
	const startScan = useApiWatcherStore((s) => s.startScan);
	const cancelScan = useApiWatcherStore((s) => s.cancelScan);
	const reset = useApiWatcherStore((s) => s.reset);

	const isScanning = phase === "scanning";
	const canRun = !!projectPath && !isScanning;

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div className="flex items-center gap-3 flex-wrap">
				{isScanning ? (
					<button
						type="button"
						onClick={() => cancelScan()}
						className="px-3 py-1.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-sm hover:bg-red-500/20"
					>
						{t("actions.cancel")}
					</button>
				) : (
					<>
						<button
							type="button"
							onClick={() => projectPath && startScan(projectPath, false)}
							disabled={!canRun}
							className="px-3 py-1.5 rounded bg-(--accent-color) text-white text-sm disabled:opacity-50"
						>
							{t("actions.runScan")}
						</button>
						<button
							type="button"
							onClick={() => projectPath && startScan(projectPath, true)}
							disabled={!canRun}
							className="px-3 py-1.5 rounded bg-(--bg-secondary) border border-(--border-color) text-sm disabled:opacity-50 hover:bg-(--bg-tertiary)"
						>
							{t("actions.saveBaseline")}
						</button>
					</>
				)}
				{result && !isScanning && (
					<button
						type="button"
						onClick={reset}
						className="px-3 py-1.5 rounded bg-(--bg-secondary) border border-(--border-color) text-sm hover:bg-(--bg-tertiary)"
					>
						{t("actions.reset")}
					</button>
				)}
			</div>

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

			{result?.diff ? (
				<ReportBody
					diff={result.diff}
					migrationGuideMarkdown={result.migrationGuideMarkdown}
					summary={result.summary}
					t={t}
				/>
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

function ReportBody({
	diff,
	migrationGuideMarkdown,
	summary,
	t,
}: {
	readonly diff: ContractDiff;
	readonly migrationGuideMarkdown: string;
	readonly summary: string;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
}): React.ReactElement {
	const hasChanges = diff.changes.length > 0;
	return (
		<div className="flex flex-col gap-4">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{summary ||
						(hasChanges
							? t("changesDetected", { count: diff.changes.length })
							: t("noChanges"))}
				</p>
			</div>

			<div className="grid grid-cols-3 gap-3">
				<div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
					<p className="text-xs text-red-400">{t("categories.breaking")}</p>
					<p className="text-2xl font-bold text-red-400">
						{diff.breakingCount}
					</p>
				</div>
				<div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
					<p className="text-xs text-yellow-400">
						{t("categories.potentiallyBreaking")}
					</p>
					<p className="text-2xl font-bold text-yellow-400">
						{diff.potentiallyBreakingCount}
					</p>
				</div>
				<div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
					<p className="text-xs text-green-400">
						{t("categories.nonBreaking")}
					</p>
					<p className="text-2xl font-bold text-green-400">
						{diff.nonBreakingCount}
					</p>
				</div>
			</div>

			<div className="space-y-2">
				{diff.changes.map((change, idx) => (
					<ChangeRow key={`${change.path}-${idx}`} change={change} />
				))}
			</div>

			{migrationGuideMarkdown && (
				<div className="mt-4 p-4 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
					<h3 className="text-sm font-medium mb-2">{t("migrationGuide")}</h3>
					<pre className="text-xs whitespace-pre-wrap font-mono text-(--text-secondary)">
						{migrationGuideMarkdown}
					</pre>
				</div>
			)}
		</div>
	);
}

function ChangeRow({
	change,
}: {
	readonly change: ContractChange;
}): React.ReactElement {
	const style =
		CATEGORY_STYLES[change.category] ?? CATEGORY_STYLES.non_breaking;
	return (
		<div
			className={`flex items-center gap-3 px-3 py-2 rounded-lg ${style.color}`}
		>
			<span>{style.icon}</span>
			<div className="flex-1 min-w-0">
				<p className="text-sm">{change.description}</p>
				<p className="text-xs opacity-70 font-mono">{change.path}</p>
			</div>
			<span className="text-xs opacity-70">
				{change.changeType.replaceAll("_", " ")}
			</span>
		</div>
	);
}
