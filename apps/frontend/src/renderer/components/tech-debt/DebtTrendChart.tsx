import { useTranslation } from "react-i18next";
import type { DebtTrendPoint } from "../../../preload/api/modules/tech-debt-api";

interface Props {
	readonly trend: DebtTrendPoint[];
}

export function DebtTrendChart({ trend }: Props) {
	const { t } = useTranslation(["techDebt"]);
	if (!trend.length) {
		return (
			<p className="text-sm text-muted-foreground py-4 text-center">
				{t("techDebt:noTrend")}
			</p>
		);
	}
	const max = Math.max(...trend.map((p) => p.total_items), 1);
	const width = 400;
	const height = 120;
	const step = trend.length > 1 ? width / (trend.length - 1) : 0;
	const points = trend
		.map((p, i) => {
			const x = i * step;
			const y = height - (p.total_items / max) * (height - 10) - 5;
			return `${x},${y}`;
		})
		.join(" ");
	const first = trend[0];
	const last = trend[trend.length - 1];
	const delta = last.total_items - first.total_items;
	return (
		<div>
			<svg
				viewBox={`0 0 ${width} ${height}`}
				className="w-full h-32"
				aria-label={t("techDebt:trendAria")}
				role="img"
			>
				<polyline
					points={points}
					fill="none"
					stroke="currentColor"
					strokeWidth={2}
				/>
			</svg>
			<div className="flex justify-between text-xs text-muted-foreground mt-1">
				<span>
					{t("techDebt:trendFrom", {
						count: first.total_items,
					})}
				</span>
				<span>
					{t("techDebt:trendTo", {
						count: last.total_items,
						delta: delta >= 0 ? `+${delta}` : String(delta),
					})}
				</span>
			</div>
		</div>
	);
}
