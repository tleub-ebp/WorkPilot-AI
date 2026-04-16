import type { UsageSnapshot } from "@shared/types";
import { formatUsageValue } from "@shared/utils/format-usage";
import { Clock, Info, TrendingUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import { getColorClass, getGradientClass } from "../../utils/usageColors";

interface DefaultUsageContentProps {
	readonly usage: UsageSnapshot;
	readonly sessionResetTime?: string;
	readonly weeklyResetTime?: string;
	readonly sessionLabel: string;
	readonly weeklyLabel: string;
}

export function DefaultUsageContent({
	usage,
	sessionResetTime,
	weeklyResetTime,
	sessionLabel,
	weeklyLabel,
}: DefaultUsageContentProps) {
	const { t } = useTranslation(["common"]);

	return (
		<>
			{/* Session/5-hour usage */}
			<div className="space-y-1.5">
				<div className="flex items-center justify-between">
					<span className="text-muted-foreground font-medium text-[11px] flex items-center gap-1">
						<Clock className="h-3 w-3" />
						{sessionLabel}
					</span>
					<span
						className={`font-semibold tabular-nums text-xs ${getColorClass(usage.sessionPercent).replace("500", "600")}`}
					>
						{Math.round(usage.sessionPercent)}%
					</span>
				</div>
				{sessionResetTime && (
					<div className="text-[10px] text-muted-foreground pl-4 flex items-center gap-1">
						<Info className="h-2.5 w-2.5" />
						{sessionResetTime}
					</div>
				)}
				<div className="h-2 bg-muted rounded-full overflow-hidden shadow-inner">
					<div
						className={`h-full rounded-full transition-all duration-500 ease-out relative overflow-hidden ${getGradientClass(usage.sessionPercent)}`}
						style={{ width: `${Math.min(usage.sessionPercent, 100)}%` }}
					>
						<div className="absolute inset-0 bg-linear-to-r from-transparent via-white/20 to-transparent motion-safe:animate-pulse" />
					</div>
				</div>
				{usage.sessionUsageValue != null && usage.sessionUsageLimit != null && (
					<div className="flex items-center justify-between text-[10px]">
						<span className="text-muted-foreground">
							{t("common:usage.used")}
						</span>
						<span className="font-medium tabular-nums">
							{formatUsageValue(usage.sessionUsageValue)}{" "}
							<span className="text-muted-foreground mx-1">/</span>{" "}
							{formatUsageValue(usage.sessionUsageLimit)}
						</span>
					</div>
				)}
			</div>

			{/* Weekly/Monthly usage */}
			<div className="space-y-1.5">
				<div className="flex items-center justify-between">
					<span className="text-muted-foreground font-medium text-[11px] flex items-center gap-1">
						<TrendingUp className="h-3 w-3" />
						{weeklyLabel}
					</span>
					<span
						className={`font-semibold tabular-nums text-xs ${usage.weeklyPercent < 0 ? "text-muted-foreground" : getColorClass(usage.weeklyPercent).replace("500", "600")}`}
					>
						{usage.weeklyPercent < 0 ? "N/A" : `${Math.round(usage.weeklyPercent)}%`}
					</span>
				</div>
				{weeklyResetTime && usage.weeklyPercent >= 0 && (
					<div className="text-[10px] text-muted-foreground pl-4 flex items-center gap-1">
						<Info className="h-2.5 w-2.5" />
						{weeklyResetTime}
					</div>
				)}
				{usage.weeklyPercent >= 0 && (
				<div className="h-2 bg-muted rounded-full overflow-hidden shadow-inner">
					<div
						className={`h-full rounded-full transition-all duration-500 ease-out relative overflow-hidden ${getGradientClass(usage.weeklyPercent)}`}
						style={{ width: `${Math.min(usage.weeklyPercent, 100)}%` }}
					>
						<div className="absolute inset-0 bg-linear-to-r from-transparent via-white/20 to-transparent motion-safe:animate-pulse" />
					</div>
				</div>
				)}
				{usage.weeklyUsageValue != null && usage.weeklyUsageLimit != null && (
					<div className="flex items-center justify-between text-[10px]">
						<span className="text-muted-foreground">
							{t("common:usage.used")}
						</span>
						<span className="font-medium tabular-nums">
							{formatUsageValue(usage.weeklyUsageValue)}{" "}
							<span className="text-muted-foreground mx-1">/</span>{" "}
							{formatUsageValue(usage.weeklyUsageLimit)}
						</span>
					</div>
				)}
			</div>
		</>
	);
}
