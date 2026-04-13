import type React from "react";
import { useTranslation } from "react-i18next";
import type { ParsedNotebook } from "../../../shared/types/notebook-agent";

interface NotebookViewProps {
	readonly notebook?: ParsedNotebook;
}

export function NotebookView({
	notebook,
}: NotebookViewProps): React.ReactElement {
	const { t } = useTranslation("notebookAgent");
	if (!notebook) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>{t("noDataAvailable")}</p>
			</div>
		);
	}
	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{notebook.path} · {notebook.kernel} · {notebook.language}
				</p>
			</div>

			<div className="grid grid-cols-4 gap-3">
				<StatCard label={t("totalCells")} value={notebook.totalCells} color="text-blue-400" />
				<StatCard label={t("codeCells")} value={notebook.codeCells} color="text-green-400" />
				<StatCard label={t("markdown")} value={notebook.markdownCells} color="text-purple-400" />
				<StatCard label={t("issues")} value={notebook.issues.length} color="text-red-400" />
			</div>

			{notebook.issues.length > 0 && (
				<div className="space-y-2">
					{notebook.issues.map((issue, idx) => {
						let severityClass: string;
						if (issue.severity === "error") {
							severityClass = "border-red-500/20 bg-red-500/10 text-red-400";
						} else if (issue.severity === "warning") {
							severityClass = "border-yellow-500/20 bg-yellow-500/10 text-yellow-400";
						} else {
							severityClass = "border-blue-500/20 bg-blue-500/10 text-blue-400";
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
