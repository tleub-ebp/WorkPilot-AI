import { useTranslation } from "react-i18next";
import type { DebtItem } from "../../../preload/api/modules/tech-debt-api";

interface Props {
	readonly items: DebtItem[];
}

export function DebtHeatmap({ items }: Props) {
	const { t } = useTranslation(["techDebt"]);
	const byFile = new Map<string, number>();
	for (const item of items) {
		byFile.set(item.file_path, (byFile.get(item.file_path) ?? 0) + item.roi);
	}
	const entries = Array.from(byFile.entries())
		.sort((a, b) => b[1] - a[1])
		.slice(0, 20);
	if (!entries.length) {
		return (
			<p className="text-sm text-muted-foreground py-4 text-center">
				{t("techDebt:empty")}
			</p>
		);
	}
	const max = entries[0][1];
	return (
		<ul className="space-y-1">
			{entries.map(([file, score]) => {
				const pct = Math.max(4, Math.round((score / max) * 100));
				return (
					<li key={file} className="text-xs">
						<div className="flex justify-between">
							<span className="font-mono truncate">{file}</span>
							<span>{score.toFixed(1)}</span>
						</div>
						<div className="h-2 bg-muted rounded">
							<div
								className="h-2 rounded bg-orange-500"
								style={{ width: `${pct}%` }}
							/>
						</div>
					</li>
				);
			})}
		</ul>
	);
}
