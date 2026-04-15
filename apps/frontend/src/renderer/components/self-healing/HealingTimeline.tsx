import type { HealingOperation } from "@shared/types/self-healing";
import { useTranslation } from "react-i18next";

interface HealingTimelineProps {
	readonly operation: HealingOperation;
}

const stepStatusColors: Record<string, string> = {
	completed: "bg-green-500",
	running: "bg-blue-500 animate-pulse",
	failed: "bg-red-500",
	pending: "bg-gray-500",
};

export function HealingTimeline({ operation }: HealingTimelineProps) {
	const { t } = useTranslation(["selfHealing"]);

	let statusColor: string;
	let statusText: string;

	if (operation.success) {
		statusColor = "bg-green-500/20 text-green-400";
		statusText = t("selfHealing:resolved");
	} else if (operation.completed_at) {
		statusColor = "bg-red-500/20 text-red-400";
		statusText = t("selfHealing:failed");
	} else {
		statusColor = "bg-blue-500/20 text-blue-400";
		statusText = t("selfHealing:inProgress");
	}

	return (
		<div className="rounded-lg border border-(--border-primary) bg-(--bg-secondary) p-4">
			<div className="flex items-center justify-between mb-3">
				<h4 className="text-sm font-medium text-(--text-primary)">
					{operation.incident?.title || t("selfHealing:healingOperation")}
				</h4>
				<span
					className={`text-xs px-2 py-0.5 rounded-full ${statusColor}`}
				>
					{statusText}
				</span>
			</div>

			<div className="relative pl-4">
				{operation.steps.map((step, index) => (
					<div
						key={`${step.name}-${step.status}`}
						className="relative pb-4 last:pb-0"
					>
						{/* Vertical line */}
						{index < operation.steps.length - 1 && (
							<div className="absolute left-0 top-3 w-px h-full bg-(--border-primary)" />
						)}
						{/* Dot */}
						<div
							className={`absolute left-0 top-1.5 w-2 h-2 rounded-full -translate-x-[3px] ${stepStatusColors[step.status] || stepStatusColors.pending}`}
						/>
						{/* Content */}
						<div className="ml-3">
							<div className="flex items-center gap-2">
								<span className="text-sm text-(--text-primary)">
									{step.name}
								</span>
							</div>
							{step.detail && (
								<p className="text-xs text-(--text-tertiary) mt-0.5">
									{step.detail}
								</p>
							)}
						</div>
					</div>
				))}
			</div>

			{operation.duration_seconds != null && (
				<div className="mt-3 text-xs text-(--text-tertiary)">
					{t("selfHealing:duration")}: {operation.duration_seconds.toFixed(1)}s
				</div>
			)}
		</div>
	);
}
