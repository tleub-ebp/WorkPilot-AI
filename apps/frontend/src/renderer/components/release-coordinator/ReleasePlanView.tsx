import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupReleaseCoordinatorListeners,
	useReleaseCoordinatorStore,
} from "../../stores/release-coordinator-store";
import type {
	GateStatus,
	ReleaseTrainPlan,
} from "../../../shared/types/release-coordinator";

const GATE_STYLES: Record<GateStatus, { color: string; icon: string }> = {
	passed: { color: "text-green-400", icon: "✅" },
	failed: { color: "text-red-400", icon: "❌" },
	pending: { color: "text-yellow-400", icon: "⏳" },
	skipped: { color: "text-gray-400", icon: "⏭️" },
};

interface ReleasePlanViewProps {
	readonly projectPath?: string;
}

export function ReleasePlanView({
	projectPath,
}: ReleasePlanViewProps): React.ReactElement {
	const { t } = useTranslation("releaseCoordinator");

	useEffect(() => {
		const cleanup = setupReleaseCoordinatorListeners();
		return cleanup;
	}, []);

	const phase = useReleaseCoordinatorStore((s) => s.phase);
	const status = useReleaseCoordinatorStore((s) => s.status);
	const plan = useReleaseCoordinatorStore((s) => s.plan);
	const error = useReleaseCoordinatorStore((s) => s.error);
	const startPlan = useReleaseCoordinatorStore((s) => s.startPlan);
	const cancelPlan = useReleaseCoordinatorStore((s) => s.cancelPlan);
	const reset = useReleaseCoordinatorStore((s) => s.reset);

	const isPlanning = phase === "planning";
	const canRun = !!projectPath && !isPlanning;

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div className="flex items-center gap-3 flex-wrap">
				{isPlanning ? (
					<button
						type="button"
						onClick={() => cancelPlan()}
						className="px-3 py-1.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-sm hover:bg-red-500/20"
					>
						{t("actions.cancel")}
					</button>
				) : (
					<button
						type="button"
						onClick={() => projectPath && startPlan(projectPath)}
						disabled={!canRun}
						className="px-3 py-1.5 rounded bg-(--accent-color) text-white text-sm disabled:opacity-50"
					>
						{t("actions.runPlan")}
					</button>
				)}
				{plan && !isPlanning && (
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

			{isPlanning && (
				<div className="text-sm text-(--text-secondary) animate-pulse">
					{status || t("actions.planning")}
				</div>
			)}

			{phase === "error" && error && (
				<div className="text-sm text-red-400">
					{t("errors.failed", { error })}
				</div>
			)}

			{plan ? (
				<PlanBody plan={plan} t={t} />
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

function PlanBody({
	plan,
	t,
}: {
	readonly plan: ReleaseTrainPlan;
	readonly t: (key: string, opts?: Record<string, unknown>) => string;
}): React.ReactElement {
	return (
		<div className="flex flex-col gap-4">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{plan.services.length} {t("services")} · {t("status")}: {plan.status}
				</p>
			</div>

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
								<p className="text-xs opacity-70 mt-0.5">{gate.message}</p>
							)}
						</div>
					);
				})}
			</div>

			<div className="space-y-2">
				{plan.services.map((svc) => {
					const version = `${svc.nextVersion.major}.${svc.nextVersion.minor}.${svc.nextVersion.patch}`;
					const current = `${svc.currentVersion.major}.${svc.currentVersion.minor}.${svc.currentVersion.patch}`;
					return (
						<div
							key={svc.name}
							className="px-4 py-3 rounded-lg border border-(--border-color) hover:bg-(--bg-secondary) transition-colors"
						>
							<div className="flex items-center justify-between mb-1">
								<p className="text-sm font-medium">{svc.name}</p>
								<span className="text-xs font-mono text-blue-400">
									{current} → {version}
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
