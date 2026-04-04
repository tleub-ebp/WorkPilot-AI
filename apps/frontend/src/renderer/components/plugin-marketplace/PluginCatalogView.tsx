import type { PluginType } from "@shared/types/plugin-marketplace";
import { Search, SlidersHorizontal } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import {
	installPlugin,
	uninstallPlugin,
	usePluginMarketplaceStore,
} from "@/stores/plugin-marketplace-store";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { PluginCard } from "./PluginCard";

const TYPE_FILTERS: Array<{ value: PluginType | "all"; labelKey: string }> = [
	{ value: "all", labelKey: "common:pluginMarketplace.filters.all" },
	{ value: "agent", labelKey: "common:pluginMarketplace.types.agent" },
	{
		value: "integration",
		labelKey: "common:pluginMarketplace.types.integration",
	},
	{
		value: "spec-template",
		labelKey: "common:pluginMarketplace.types.specTemplate",
	},
	{ value: "theme", labelKey: "common:pluginMarketplace.types.theme" },
	{
		value: "custom-prompt",
		labelKey: "common:pluginMarketplace.types.customPrompt",
	},
];

export function PluginCatalogView() {
	const { t } = useTranslation(["common"]);
	const {
		filters,
		setFilters,
		isInstalling,
		isCatalogLoading,
		getFilteredCatalog,
		isPluginInstalled,
	} = usePluginMarketplaceStore();

	const filteredPlugins = getFilteredCatalog();

	return (
		<div className="flex flex-col h-full">
			{/* Filters bar */}
			<div className="shrink-0 border-b border-border px-6 py-3 space-y-3">
				{/* Search + sort */}
				<div className="flex items-center gap-3">
					<div className="relative flex-1">
						<Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
						<Input
							placeholder={t("common:pluginMarketplace.searchPlaceholder")}
							value={filters.search}
							onChange={(e) => setFilters({ search: e.target.value })}
							className="pl-9 h-8 text-sm"
						/>
					</div>
					<div className="flex items-center gap-2">
						<select
							value={filters.sortBy}
							onChange={(e) =>
								setFilters({ sortBy: e.target.value as typeof filters.sortBy })
							}
							className="h-8 rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
						>
							<option value="popular">
								{t("common:pluginMarketplace.sort.popular")}
							</option>
							<option value="rating">
								{t("common:pluginMarketplace.sort.rating")}
							</option>
							<option value="newest">
								{t("common:pluginMarketplace.sort.newest")}
							</option>
							<option value="name">
								{t("common:pluginMarketplace.sort.name")}
							</option>
						</select>
						<Button
							variant={filters.showVerifiedOnly ? "default" : "outline"}
							size="sm"
							className="h-8 text-xs gap-1.5"
							onClick={() =>
								setFilters({ showVerifiedOnly: !filters.showVerifiedOnly })
							}
						>
							<SlidersHorizontal className="h-3 w-3" />
							{t("common:pluginMarketplace.filters.verified")}
						</Button>
					</div>
				</div>

				{/* Type filter pills */}
				<div className="flex items-center gap-2 overflow-x-auto pb-0.5">
					{TYPE_FILTERS.map(({ value, labelKey }) => (
						<button
							key={value}
							type="button"
							onClick={() => setFilters({ type: value })}
							className={cn(
								"shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors",
								filters.type === value
									? "bg-primary text-primary-foreground"
									: "bg-muted text-muted-foreground hover:bg-muted/80",
							)}
						>
							{t(labelKey)}
						</button>
					))}
				</div>
			</div>

			{/* Plugin grid */}
			<div className="flex-1 overflow-y-auto px-6 py-4">
				{isCatalogLoading ? (
					<div className="flex items-center justify-center h-32">
						<div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
					</div>
				) : filteredPlugins.length === 0 ? (
					<div className="flex flex-col items-center justify-center h-32 text-muted-foreground text-sm">
						<p>{t("common:pluginMarketplace.noResults")}</p>
					</div>
				) : (
					<>
						<p className="text-xs text-muted-foreground mb-4">
							{t("common:pluginMarketplace.resultsCount", {
								count: filteredPlugins.length,
							})}
						</p>
						<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
							{filteredPlugins.map((plugin) => (
								<PluginCard
									key={plugin.id}
									plugin={plugin}
									isInstalled={isPluginInstalled(plugin.id)}
									isInstalling={isInstalling === plugin.id}
									onInstall={() => installPlugin(plugin.id)}
									onUninstall={() => uninstallPlugin(plugin.id)}
								/>
							))}
						</div>
					</>
				)}
			</div>
		</div>
	);
}
