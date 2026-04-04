import type { IncidentMode } from "@shared/types/self-healing";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useProjectStore } from "@/stores/project-store";
import { useSelfHealingStore } from "@/stores/self-healing-store";
import { CICDTab } from "./CICDTab";
import { ProactiveTab } from "./ProactiveTab";
import { ProductionTab } from "./ProductionTab";

const TABS: Array<{ id: IncidentMode; icon: string; labelKey: string }> = [
	{ id: "cicd", icon: "\uD83D\uDD04", labelKey: "selfHealing:tabCICD" },
	{
		id: "production",
		icon: "\uD83C\uDFED",
		labelKey: "selfHealing:tabProduction",
	},
	{
		id: "proactive",
		icon: "\uD83D\uDD2E",
		labelKey: "selfHealing:tabProactive",
	},
];

export function SelfHealingDashboard() {
	const { t } = useTranslation(["selfHealing", "common"]);
	const { activeTab, setActiveTab, stats, isLoading, error, fetchDashboard } =
		useSelfHealingStore();
	const selectedProject = useProjectStore((s) => s.getSelectedProject?.());
	const projectPath = selectedProject?.path || "";

	useEffect(() => {
		if (projectPath) {
			fetchDashboard(projectPath);
		}
	}, [projectPath, fetchDashboard]);

	return (
		<div className="h-full flex flex-col overflow-hidden">
			{/* Header */}
			<div className="px-6 py-4 border-b border-[var(--border-primary)] bg-[var(--bg-primary)]">
				<div className="flex items-center justify-between">
					<div>
						<h1 className="text-lg font-semibold text-[var(--text-primary)]">
							{t("selfHealing:title")}
						</h1>
						<p className="text-xs text-[var(--text-tertiary)] mt-0.5">
							{t("selfHealing:subtitle")}
						</p>
					</div>
				</div>

				{/* Stats summary */}
				<div className="grid grid-cols-5 gap-3 mt-3">
					<StatCard
						label={t("selfHealing:totalIncidents")}
						value={stats.totalIncidents}
					/>
					<StatCard
						label={t("selfHealing:resolved")}
						value={stats.resolvedIncidents}
						variant="success"
					/>
					<StatCard
						label={t("selfHealing:active")}
						value={stats.activeIncidents}
						variant={stats.activeIncidents > 0 ? "warning" : "default"}
					/>
					<StatCard
						label={t("selfHealing:avgResolution")}
						value={`${stats.avgResolutionTime}s`}
					/>
					<StatCard
						label={t("selfHealing:autoFixRate")}
						value={`${stats.autoFixRate}%`}
						variant="success"
					/>
				</div>
			</div>

			{/* Tab bar */}
			<div className="flex border-b border-[var(--border-primary)] bg-[var(--bg-primary)] px-6">
				{TABS.map((tab) => (
					<button
						key={tab.id}
						type="button"
						onClick={() => setActiveTab(tab.id)}
						className={`flex items-center gap-1.5 px-4 py-2.5 text-sm border-b-2 transition-colors ${
							activeTab === tab.id
								? "border-[var(--accent-primary)] text-[var(--accent-primary)]"
								: "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
						}`}
					>
						<span>{tab.icon}</span>
						<span>{t(tab.labelKey)}</span>
					</button>
				))}
			</div>

			{/* Error banner */}
			{error && (
				<div className="px-6 py-2 bg-red-500/10 border-b border-red-500/20">
					<p className="text-xs text-red-400">{error}</p>
				</div>
			)}

			{/* Tab content */}
			<div className="flex-1 overflow-y-auto px-6 py-4">
				{isLoading ? (
					<div className="flex items-center justify-center h-32">
						<div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--accent-primary)]" />
					</div>
				) : (
					<>
						{activeTab === "cicd" && <CICDTab projectPath={projectPath} />}
						{activeTab === "production" && (
							<ProductionTab projectPath={projectPath} />
						)}
						{activeTab === "proactive" && (
							<ProactiveTab projectPath={projectPath} />
						)}
					</>
				)}
			</div>
		</div>
	);
}

// ── Stat Card Component ─────────────────────────────────────

interface StatCardProps {
	readonly label: string;
	readonly value: number | string;
	readonly variant?: "default" | "success" | "warning";
}

function StatCard({ label, value, variant = "default" }: StatCardProps) {
	const valueColors = {
		default: "text-[var(--text-primary)]",
		success: "text-green-400",
		warning: "text-yellow-400",
	};

	return (
		<div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] p-2.5">
			<p className="text-xs text-[var(--text-tertiary)]">{label}</p>
			<p className={`text-lg font-semibold ${valueColors[variant]}`}>{value}</p>
		</div>
	);
}
