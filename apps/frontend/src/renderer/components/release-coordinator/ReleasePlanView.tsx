import type React from "react";
import { useTranslation } from "react-i18next";
import type {
	ReleaseTrainPlan,
	GateStatus,
} from "../../../shared/types/release-coordinator";

const GATE_STYLES: Record<GateStatus, { color: string; icon: string }> = {
	passed: { color: "text-green-400", icon: "✅" },
	failed: { color: "text-red-400", icon: "❌" },
	pending: { color: "text-yellow-400", icon: "⏳" },
	skipped: { color: "text-gray-400", icon: "⏭️" },
};

interface ReleasePlanViewProps {
	readonly plan?: ReleaseTrainPlan;
	readonly onRelease?: () => void;
}

export function ReleasePlanView({
	plan,
	onRelease,
}: ReleasePlanViewProps): React.ReactElement {
	const { t } = useTranslation("releaseCoordinator");
	if (!plan) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>{t("noData")}</p>
			</div>
		);
	}
	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-lg font-semibold">{t("title")}</h2>
					<p className="text-sm text-(--text-secondary)">
						{plan.services.length} {t("services")} · {t("status")}: {plan.status}
					</p>
				</div>
				{onRelease && plan.allGatesPassed && (
					<button
						type="button"
						onClick={onRelease}
						className="px-4 py-2 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors text-sm font-medium"
					>
						{t("shipIt")}
					</button>
				)}
			</div>

			{/* Gates */}
			<div className="grid grid-cols-4 gap-2">
				{plan.gates.map((gate) => {
					const style = GATE_STYLES[gate.status];
					return (
						<div
							key={gate.name}
							className={`p-2 rounded-lg border border-(--border-color) ${style.color}`}
						>
							<div className="flex items-center gap-1 text-xs">
								<span>{style.icon}</span>
								<span className="font-medium">{gate.name}</span>
							</div>
							{gate.message && (
								<p className="text-xs opacity-70 mt-0.5">
									{gate.message}
								</p>
							)}
						</div>
					);
				})}
			</div>

			{/* Services */}
			<div className="space-y-2">
				{plan.services.map((svc) => {
					const version = `${svc.nextVersion.major}.${svc.nextVersion.minor}.${svc.nextVersion.patch}`;
					return (
						<div
							key={svc.name}
							className="px-4 py-3 rounded-lg border border-(--border-color) hover:bg-(--bg-secondary) transition-colors"
						>
							<div className="flex items-center justify-between mb-1">
								<p className="text-sm font-medium">{svc.name}</p>
								<span className="text-xs font-mono text-blue-400">
									→ {version}
								</span>
							</div>
							<div className="flex items-center gap-2 text-xs text-(--text-secondary)">
								<span className="uppercase">{svc.bumpType}</span>
								<span>·</span>
								<span>
									{svc.changelogEntries.length} {t("changelogEntries")}
								</span>
							</div>
						</div>
					);
				})}
			</div>

			{plan.summary && (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{plan.summary}
				</p>
			)}
		</div>
	);
}
