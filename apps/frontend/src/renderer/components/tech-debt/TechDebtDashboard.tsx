import { FileWarning, Gauge, RefreshCw, Wand2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useTechDebtStore } from "../../stores/tech-debt-store";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { DebtHeatmap } from "./DebtHeatmap";
import { DebtItemsTable } from "./DebtItemsTable";
import { DebtTrendChart } from "./DebtTrendChart";

interface Props {
	readonly projectPath?: string;
}

export function TechDebtDashboard({ projectPath }: Props) {
	const { t } = useTranslation(["techDebt", "common"]);
	const {
		items,
		trend,
		summary,
		filters,
		scanning,
		error,
		lastScannedAt,
		setFilter,
		scan,
		generateSpec,
	} = useTechDebtStore();

	const [projectInput, setProjectInput] = useState(projectPath ?? "");
	const [specCreated, setSpecCreated] = useState<string | null>(null);

	useEffect(() => {
		if (projectPath && !items.length && !scanning) {
			void scan(projectPath);
		}
	}, [projectPath, items.length, scanning, scan]);

	const filteredItems = useMemo(() => {
		return items.filter((item) => {
			if (item.roi < filters.minScore) return false;
			if (filters.kind && item.kind !== filters.kind) return false;
			if (
				filters.search &&
				!`${item.file_path} ${item.message}`
					.toLowerCase()
					.includes(filters.search.toLowerCase())
			)
				return false;
			return true;
		});
	}, [items, filters]);

	const topItems = useMemo(
		() => [...filteredItems].sort((a, b) => b.roi - a.roi).slice(0, 10),
		[filteredItems],
	);

	const canScan = !scanning && !!projectInput.trim();

	const handleScan = () => {
		if (canScan) void scan(projectInput.trim());
	};

	const handleGenerateSpec = async (itemId: string) => {
		if (!projectInput.trim()) return;
		const dir = await generateSpec(projectInput.trim(), itemId);
		if (dir) setSpecCreated(dir);
	};

	return (
		<div className="p-6 space-y-6">
			<header className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-semibold flex items-center gap-2">
						<Gauge className="h-6 w-6" />
						{t("techDebt:title")}
					</h1>
					<p className="text-sm text-muted-foreground">
						{t("techDebt:description")}
					</p>
				</div>
				<Button onClick={handleScan} disabled={!canScan}>
					<RefreshCw
						className={`h-4 w-4 mr-2 ${scanning ? "animate-spin" : ""}`}
					/>
					{t("techDebt:actions.scan")}
				</Button>
			</header>

			<section className="grid grid-cols-1 md:grid-cols-3 gap-3">
				<div>
					<Label htmlFor="td-project">{t("techDebt:fields.projectPath")}</Label>
					<Input
						id="td-project"
						value={projectInput}
						onChange={(e) => setProjectInput(e.target.value)}
						placeholder="/abs/path/to/project"
					/>
				</div>
				<div>
					<Label htmlFor="td-min">{t("techDebt:fields.minScore")}</Label>
					<Input
						id="td-min"
						type="number"
						step={0.1}
						value={filters.minScore}
						onChange={(e) =>
							setFilter("minScore", Number(e.target.value) || 0)
						}
					/>
				</div>
				<div>
					<Label htmlFor="td-search">{t("techDebt:fields.search")}</Label>
					<Input
						id="td-search"
						value={filters.search}
						onChange={(e) => setFilter("search", e.target.value)}
						placeholder={t("techDebt:fields.searchPlaceholder")}
					/>
				</div>
			</section>

			{error && (
				<div className="p-3 rounded-md border border-destructive/40 bg-destructive/10 text-sm flex items-center gap-2">
					<FileWarning className="h-4 w-4" />
					{error}
				</div>
			)}

			{summary && (
				<section className="grid grid-cols-2 md:grid-cols-4 gap-3">
					<SummaryCard
						label={t("techDebt:summary.total")}
						value={String(summary.total)}
					/>
					<SummaryCard
						label={t("techDebt:summary.totalCost")}
						value={String(summary.total_cost)}
					/>
					<SummaryCard
						label={t("techDebt:summary.totalEffort")}
						value={String(summary.total_effort)}
					/>
					<SummaryCard
						label={t("techDebt:summary.avgRoi")}
						value={String(summary.avg_roi)}
					/>
				</section>
			)}

			<section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<div className="border rounded-md p-4">
					<h2 className="text-sm font-medium mb-3">
						{t("techDebt:sections.trend")}
					</h2>
					<DebtTrendChart trend={trend} />
				</div>
				<div className="border rounded-md p-4">
					<h2 className="text-sm font-medium mb-3">
						{t("techDebt:sections.heatmap")}
					</h2>
					<DebtHeatmap items={filteredItems} />
				</div>
			</section>

			<section className="border rounded-md p-4">
				<div className="flex items-center justify-between mb-3">
					<h2 className="text-sm font-medium">
						{t("techDebt:sections.top", { count: topItems.length })}
					</h2>
					{lastScannedAt && (
						<span className="text-xs text-muted-foreground">
							{t("techDebt:lastScanned", {
								when: new Date(lastScannedAt * 1000).toLocaleString(),
							})}
						</span>
					)}
				</div>
				<DebtItemsTable
					items={topItems}
					onGenerateSpec={handleGenerateSpec}
				/>
			</section>

			{specCreated && (
				<div className="p-3 rounded-md border bg-muted/40 text-sm flex items-center gap-2">
					<Wand2 className="h-4 w-4" />
					{t("techDebt:specCreated", { path: specCreated })}
				</div>
			)}
		</div>
	);
}

function SummaryCard({ label, value }: { label: string; value: string }) {
	return (
		<div className="border rounded-md p-3">
			<div className="text-xs text-muted-foreground">{label}</div>
			<div className="text-lg font-semibold">{value}</div>
		</div>
	);
}
