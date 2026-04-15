import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupNotebookAgentListeners,
	useNotebookAgentStore,
} from "../../stores/notebook-agent-store";
import type { ParsedNotebook } from "../../../shared/types/notebook-agent";

interface NotebookViewProps {
	readonly projectPath?: string;
}

export function NotebookView({
	projectPath,
}: NotebookViewProps): React.ReactElement {
	const { t } = useTranslation("notebookAgent");

	useEffect(() => {
		const cleanup = setupNotebookAgentListeners();
		return cleanup;
	}, []);

	const phase = useNotebookAgentStore((s) => s.phase);
	const status = useNotebookAgentStore((s) => s.status);
	const notebooks = useNotebookAgentStore((s) => s.notebooks);
	const error = useNotebookAgentStore((s) => s.error);
	const startScan = useNotebookAgentStore((s) => s.startScan);
	const cancelScan = useNotebookAgentStore((s) => s.cancelScan);
	const reset = useNotebookAgentStore((s) => s.reset);

	const isScanning = phase === "scanning";
	const canRun = !!projectPath && !isScanning;
	const hasResults = notebooks.length > 0;

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
					<button
						type="button"
						onClick={() => projectPath && startScan(projectPath)}
						disabled={!canRun}
						className="px-3 py-1.5 rounded bg-(--accent-color) text-white text-sm disabled:opacity-50"
					>
						{t("actions.runScan")}
					</button>
				)}
				{hasResults && !isScanning && (
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

			{hasResults ? (
				<div className="flex flex-col gap-6">
					{notebooks.map((nb) => (
						<NotebookReport key={nb.path} notebook={nb} t={t} />
					))}
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

function NotebookReport({
	notebook,
	t,
}: {
	readonly notebook: ParsedNotebook;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
}): React.ReactElement {
	return (
		<div className="flex flex-col gap-3">
			<div>
				<h3 className="text-base font-semibold">{notebook.path}</h3>
				<p className="text-xs text-(--text-secondary)">
					{notebook.kernel} · {notebook.language}
				</p>
			</div>

			<div className="grid grid-cols-4 gap-3">
				<StatCard
					label={t("totalCells")}
					value={notebook.totalCells}
					color="text-blue-400"
				/>
				<StatCard
					label={t("codeCells")}
					value={notebook.codeCells}
					color="text-green-400"
				/>
				<StatCard
					label={t("markdown")}
					value={notebook.markdownCells}
					color="text-purple-400"
				/>
				<StatCard
					label={t("issues")}
					value={notebook.issues.length}
					color="text-red-400"
				/>
			</div>

			{notebook.issues.length > 0 && (
				<div className="space-y-2">
					{notebook.issues.map((issue, idx) => {
						let severityClass: string;
						if (issue.severity === "error") {
							severityClass =
								"border-red-500/20 bg-red-500/10 text-red-400";
						} else if (issue.severity === "warning") {
							severityClass =
								"border-yellow-500/20 bg-yellow-500/10 text-yellow-400";
						} else {
							severityClass =
								"border-blue-500/20 bg-blue-500/10 text-blue-400";
						}
						return (
							<div
								key={`${issue.cellIndex}-${idx}`}
								className={`px-4 py-3 rounded-lg border ${severityClass}`}
							>
								<div className="flex items-center gap-2 mb-1">
									<span className="text-xs font-medium uppercase">
										{issue.severity}
									</span>
									<span className="text-xs opacity-70">
										{t("cellIndex", { index: issue.cellIndex })} ·{" "}
										{issue.issueType.replaceAll("_", " ")}
									</span>
								</div>
								<p className="text-sm">{issue.message}</p>
								{issue.suggestion && (
									<p className="text-xs mt-1 text-green-400">
										💡 {t("suggestion")}: {issue.suggestion}
									</p>
								)}
							</div>
						);
					})}
				</div>
			)}
		</div>
	);
}

function StatCard({
	label,
	value,
	color,
}: {
	readonly label: string;
	readonly value: number;
	readonly color: string;
}): React.ReactElement {
	return (
		<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
			<p className="text-xs text-(--text-secondary)">{label}</p>
			<p className={`text-2xl font-bold ${color}`}>{value}</p>
		</div>
	);
}
