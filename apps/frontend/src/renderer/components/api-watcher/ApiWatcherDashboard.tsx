import type React from "react";
import { useTranslation } from "react-i18next";
import type { ContractDiff, ContractChange } from "../../../shared/types/api-watcher";

const CATEGORY_STYLES: Record<string, { color: string; icon: string }> = {
	breaking: { color: "text-red-400 bg-red-500/10", icon: "🔴" },
	potentially_breaking: { color: "text-yellow-400 bg-yellow-500/10", icon: "🟡" },
	non_breaking: { color: "text-green-400 bg-green-500/10", icon: "🟢" },
};

interface ApiWatcherDashboardProps {
	readonly diff?: ContractDiff;
	readonly migrationGuideMarkdown?: string;
}

export function ApiWatcherDashboard({
	diff,
	migrationGuideMarkdown,
}: ApiWatcherDashboardProps): React.ReactElement {
	const { t } = useTranslation("apiWatcher");

	if (!diff) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>{t("noData")}</p>
			</div>
		);
	}
	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{t("changesDetected", { count: diff.changes.length })}
				</p>
			</div>

			<div className="grid grid-cols-3 gap-3">
				<div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
					<p className="text-xs text-red-400">{t("categories.breaking")}</p>
					<p className="text-2xl font-bold text-red-400">{diff.breakingCount}</p>
				</div>
				<div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
					<p className="text-xs text-yellow-400">{t("categories.potentiallyBreaking")}</p>
					<p className="text-2xl font-bold text-yellow-400">{diff.potentiallyBreakingCount}</p>
				</div>
				<div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
					<p className="text-xs text-green-400">{t("categories.nonBreaking")}</p>
					<p className="text-2xl font-bold text-green-400">{diff.nonBreakingCount}</p>
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

function ChangeRow({ change }: { readonly change: ContractChange }): React.ReactElement {
	const style = CATEGORY_STYLES[change.category] ?? CATEGORY_STYLES.non_breaking;
	return (
		<div className={`flex items-center gap-3 px-3 py-2 rounded-lg ${style.color}`}>
			<span>{style.icon}</span>
			<div className="flex-1 min-w-0">
				<p className="text-sm">{change.description}</p>
				<p className="text-xs opacity-70 font-mono">{change.path}</p>
			</div>
			<span className="text-xs opacity-70">{change.changeType.replaceAll("_", " ")}</span>
		</div>
	);
}
