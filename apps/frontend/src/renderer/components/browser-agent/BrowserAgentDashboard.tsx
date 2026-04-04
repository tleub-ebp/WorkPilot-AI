import type { BrowserAgentTab } from "@shared/types/browser-agent";
import {
	AlertTriangle,
	BarChart3,
	Camera,
	FlaskConical,
	Globe,
	MonitorX,
	ScanEye,
	TestTube2,
} from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useBrowserAgentStore } from "@/stores/browser-agent-store";
import { useProjectStore } from "@/stores/project-store";
import { BrowserTab } from "./BrowserTab";
import { TestRunnerTab } from "./TestRunnerTab";
import { VisualRegressionTab } from "./VisualRegressionTab";

const TABS: Array<{
	id: BrowserAgentTab;
	icon: typeof Globe;
	labelKey: string;
	color: string;
	activeColor: string;
}> = [
	{
		id: "browser",
		icon: Globe,
		labelKey: "browserAgent:tabs.browser",
		color: "text-blue-400",
		activeColor: "border-blue-400 text-blue-400",
	},
	{
		id: "visual-regression",
		icon: ScanEye,
		labelKey: "browserAgent:tabs.visualRegression",
		color: "text-purple-400",
		activeColor: "border-purple-400 text-purple-400",
	},
	{
		id: "test-runner",
		icon: FlaskConical,
		labelKey: "browserAgent:tabs.testRunner",
		color: "text-emerald-400",
		activeColor: "border-emerald-400 text-emerald-400",
	},
];

export function BrowserAgentDashboard() {
	const { t } = useTranslation(["browserAgent", "common"]);
	const { activeTab, setActiveTab, stats, isLoading, error, fetchDashboard } =
		useBrowserAgentStore();
	const selectedProject = useProjectStore((s) => s.getSelectedProject?.());
	const projectPath = selectedProject?.path || "";

	useEffect(() => {
		if (projectPath) {
			fetchDashboard(projectPath);
		}
	}, [projectPath, fetchDashboard]);

	if (!projectPath) {
		return (
			<div className="h-full flex flex-col items-center justify-center gap-3">
				<div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
					<MonitorX className="w-7 h-7 text-blue-400 opacity-60" />
				</div>
				<p className="text-sm text-[var(--text-tertiary)]">
					{t("browserAgent:errors.noProject")}
				</p>
			</div>
		);
	}

	return (
		<div className="h-full flex flex-col overflow-hidden">
			{/* Header */}
			<div className="px-6 py-4 border-b border-[var(--border-primary)] bg-[var(--bg-primary)]">
				<div className="flex items-center gap-3 mb-4">
					<div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-blue-500/30 flex items-center justify-center">
						<Globe className="w-5 h-5 text-blue-400" />
					</div>
					<div>
						<h1 className="text-lg font-semibold text-[var(--text-primary)]">
							{t("browserAgent:title")}
						</h1>
						<p className="text-xs text-[var(--text-tertiary)]">
							{t("browserAgent:subtitle")}
						</p>
					</div>
				</div>

				{/* Stats summary */}
				<div className="grid grid-cols-4 gap-3">
					<StatCard
						icon={TestTube2}
						label={t("browserAgent:stats.totalTests")}
						value={stats.totalTests}
						color="blue"
					/>
					<StatCard
						icon={BarChart3}
						label={t("browserAgent:stats.passRate")}
						value={`${stats.passRate.toFixed(0)}%`}
						color={
							stats.passRate >= 80
								? "emerald"
								: stats.passRate > 0
									? "amber"
									: "emerald"
						}
					/>
					<StatCard
						icon={Camera}
						label={t("browserAgent:stats.screenshots")}
						value={stats.screenshotsCaptured}
						color="purple"
					/>
					<StatCard
						icon={AlertTriangle}
						label={t("browserAgent:stats.regressions")}
						value={stats.regressionsDetected}
						color={stats.regressionsDetected > 0 ? "orange" : "orange"}
					/>
				</div>
			</div>

			{/* Tab bar */}
			<div className="flex border-b border-[var(--border-primary)] bg-[var(--bg-primary)] px-6">
				{TABS.map((tab) => {
					const Icon = tab.icon;
					const isActive = activeTab === tab.id;
					return (
						<button
							key={tab.id}
							type="button"
							onClick={() => setActiveTab(tab.id)}
							className={`flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 transition-colors ${
								isActive
									? tab.activeColor
									: "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
							}`}
						>
							<Icon className={`w-4 h-4 ${isActive ? "" : ""}`} />
							<span>{t(tab.labelKey)}</span>
						</button>
					);
				})}
			</div>

			{/* Error banner */}
			{error && (
				<div className="px-6 py-2 bg-red-500/10 border-b border-red-500/20 flex items-center gap-2">
					<AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
					<p className="text-xs text-red-400">{error}</p>
				</div>
			)}

			{/* Tab content */}
			<div className="flex-1 overflow-y-auto px-6 py-4">
				{isLoading ? (
					<div className="flex flex-col items-center justify-center h-48 gap-3">
						<div className="w-7 h-7 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
						<p className="text-xs text-[var(--text-tertiary)]">
							{t("browserAgent:browser.launching")}
						</p>
					</div>
				) : (
					<>
						{activeTab === "browser" && (
							<BrowserTab projectPath={projectPath} />
						)}
						{activeTab === "visual-regression" && (
							<VisualRegressionTab projectPath={projectPath} />
						)}
						{activeTab === "test-runner" && (
							<TestRunnerTab projectPath={projectPath} />
						)}
					</>
				)}
			</div>
		</div>
	);
}

// ── StatCard component ──────────────────────────────────────

type StatColor = "blue" | "emerald" | "purple" | "orange" | "amber";

const STAT_COLORS: Record<
	StatColor,
	{ icon: string; value: string; bg: string; border: string }
> = {
	blue: {
		icon: "text-blue-400",
		value: "text-blue-400",
		bg: "bg-blue-500/10",
		border: "border-blue-500/20",
	},
	emerald: {
		icon: "text-emerald-400",
		value: "text-emerald-400",
		bg: "bg-emerald-500/10",
		border: "border-emerald-500/20",
	},
	purple: {
		icon: "text-purple-400",
		value: "text-purple-400",
		bg: "bg-purple-500/10",
		border: "border-purple-500/20",
	},
	orange: {
		icon: "text-orange-400",
		value: "text-orange-400",
		bg: "bg-orange-500/10",
		border: "border-orange-500/20",
	},
	amber: {
		icon: "text-amber-400",
		value: "text-amber-400",
		bg: "bg-amber-500/10",
		border: "border-amber-500/20",
	},
};

function StatCard({
	icon: Icon,
	label,
	value,
	color,
}: {
	readonly icon: typeof Globe;
	readonly label: string;
	readonly value: string | number;
	readonly color: StatColor;
}) {
	const colors = STAT_COLORS[color];

	return (
		<div
			className={`px-3 py-2.5 rounded-lg ${colors.bg} border ${colors.border} flex items-center gap-3`}
		>
			<Icon className={`w-4.5 h-4.5 ${colors.icon} shrink-0`} />
			<div className="min-w-0">
				<p className="text-[11px] text-[var(--text-tertiary)] truncate">
					{label}
				</p>
				<p className={`text-lg font-semibold ${colors.value} leading-tight`}>
					{value}
				</p>
			</div>
		</div>
	);
}
