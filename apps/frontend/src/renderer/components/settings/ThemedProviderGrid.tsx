import { Filter, Grid3x3, List, Plus, RefreshCw, Search } from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { ThemedProviderCard } from "./ThemedProviderCard";

interface Provider {
	id: string;
	name: string;
	category: string;
	description?: string;
	isConfigured: boolean;
	isWorking?: boolean;
	lastTested?: string;
	usageCount?: number;
	isPremium?: boolean;
	icon?: React.ReactNode;
	authType?: "oauth" | "api_key" | "cli" | "none";
	apiKeyMasked?: string;
}

interface ThemedProviderGridProps {
	providers: Provider[];
	onConfigure: (providerId: string) => void;
	onTest: (providerId: string) => void;
	onToggle: (providerId: string, enabled: boolean) => void;
	onRemove?: (providerId: string) => void;
	onAddProvider?: () => void;
	onRefreshProviders?: () => void;
	isLoading?: boolean;
	className?: string;
}

type ViewMode = "grid" | "list";
type FilterStatus = "all" | "configured" | "unconfigured" | "errors";
type SortBy = "name" | "category" | "status" | "usage";

export function ThemedProviderGrid({
	providers,
	onConfigure,
	onTest,
	onToggle,
	onRemove,
	onAddProvider,
	onRefreshProviders,
	isLoading = false,
	className,
}: ThemedProviderGridProps) {
	const { t } = useTranslation("settings");
	const [searchQuery, setSearchQuery] = useState("");
	const [viewMode, setViewMode] = useState<ViewMode>("grid");
	const [filterStatus, setFilterStatus] = useState<FilterStatus>("all");
	const [sortBy, setSortBy] = useState<SortBy>("name");

	// Filtres et recherche
	const filteredAndSortedProviders = useMemo(() => {
		const filtered = providers.filter((provider) => {
			const matchesSearch =
				provider.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				provider.description?.toLowerCase().includes(searchQuery.toLowerCase());

			const matchesFilter =
				filterStatus === "all" ||
				(filterStatus === "configured" && provider.isConfigured) ||
				(filterStatus === "unconfigured" && !provider.isConfigured) ||
				(filterStatus === "errors" && provider.isWorking === false);

			return matchesSearch && matchesFilter;
		});

		// Tri
		filtered.sort((a, b) => {
			switch (sortBy) {
				case "name":
					return a.name.localeCompare(b.name);
				case "category":
					return a.category.localeCompare(b.category);
				case "status": {
					const statusA = a.isConfigured ? (a.isWorking === false ? -1 : 1) : 0;
					const statusB = b.isConfigured ? (b.isWorking === false ? -1 : 1) : 0;
					return statusB - statusA;
				}
				case "usage":
					return (b.usageCount || 0) - (a.usageCount || 0);
				default:
					return 0;
			}
		});

		return filtered;
	}, [providers, searchQuery, filterStatus, sortBy]);

	// Statistiques
	const stats = useMemo(() => {
		const total = providers.length;
		const configured = providers.filter((p) => p.isConfigured).length;
		const working = providers.filter((p) => p.isWorking !== false).length;
		const errors = providers.filter((p) => p.isWorking === false).length;

		return { total, configured, working, errors };
	}, [providers]);

	const _categories = useMemo(() => {
		const cats = new Set(providers.map((p) => p.category));
		return Array.from(cats).sort();
	}, [providers]);

	return (
		<div className={cn("space-y-6", className)}>
			{/* Header */}
			<div className="flex flex-col gap-4">
				<div className="flex items-center justify-between">
					<div>
						<h2 className="text-lg font-semibold">{t("providerGrid.title")}</h2>
						<p className="text-sm text-gray-600">
							{t("providerGrid.description")}
						</p>
					</div>

					<div className="flex gap-2">
						{onRefreshProviders && (
							<Button
								variant="outline"
								onClick={onRefreshProviders}
								disabled={isLoading}
								size="sm"
							>
								<RefreshCw
									className={cn("w-4 h-4 mr-2", isLoading && "animate-spin")}
								/>
								{t("providerGrid.actions.refresh")}
							</Button>
						)}
						{onAddProvider && (
							<Button onClick={onAddProvider} size="sm">
								<Plus className="w-4 h-4 mr-2" />
								{t("providerGrid.actions.add")}
							</Button>
						)}
					</div>
				</div>

				{/* Statistiques */}
				<div className="flex gap-4 text-sm">
					<div className="px-3 py-1 bg-gray-100 rounded">
						{t("providerGrid.stats.total", { count: stats.total })}
					</div>
					<div className="px-3 py-1 bg-green-100 text-green-700 rounded">
						{t("providerGrid.stats.configured", { count: stats.configured })}
					</div>
					{stats.errors > 0 && (
						<div className="px-3 py-1 bg-red-100 text-red-700 rounded">
							{t("providerGrid.stats.errors", { count: stats.errors })}
						</div>
					)}
				</div>
			</div>

			{/* Barre de recherche et filtres */}
			<div className="border rounded-lg p-4 space-y-4 bg-gray-50">
				<div className="flex flex-col lg:flex-row gap-4">
					<div className="flex-1">
						<div className="relative">
							<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
							<Input
								placeholder={t("providerGrid.search.placeholder")}
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								className="pl-10"
							/>
						</div>
					</div>

					<div className="flex gap-2">
						<Select
							value={sortBy}
							onValueChange={(value: SortBy) => setSortBy(value)}
						>
							<SelectTrigger className="w-44">
								<SelectValue placeholder={t("providerGrid.sort.placeholder")} />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="name">
									{t("providerGrid.sort.name")}
								</SelectItem>
								<SelectItem value="category">
									{t("providerGrid.sort.category")}
								</SelectItem>
								<SelectItem value="status">
									{t("providerGrid.sort.status")}
								</SelectItem>
								<SelectItem value="usage">
									{t("providerGrid.sort.usage")}
								</SelectItem>
							</SelectContent>
						</Select>

						<Select
							value={filterStatus}
							onValueChange={(value: FilterStatus) => setFilterStatus(value)}
						>
							<SelectTrigger className="w-44">
								<Filter className="w-4 h-4 mr-2 text-gray-500" />
								<SelectValue
									placeholder={t("providerGrid.filters.placeholder")}
								/>
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="all">
									{t("providerGrid.filters.all")}
								</SelectItem>
								<SelectItem value="configured">
									{t("providerGrid.filters.configured")}
								</SelectItem>
								<SelectItem value="unconfigured">
									{t("providerGrid.filters.unconfigured")}
								</SelectItem>
								<SelectItem value="errors">
									{t("providerGrid.filters.errors")}
								</SelectItem>
							</SelectContent>
						</Select>

						<div className="flex bg-gray-200 rounded p-1">
							<Button
								variant={viewMode === "grid" ? "default" : "ghost"}
								size="sm"
								onClick={() => setViewMode("grid")}
								className="h-7 px-2"
							>
								<Grid3x3 className="w-3 h-3" />
							</Button>
							<Button
								variant={viewMode === "list" ? "default" : "ghost"}
								size="sm"
								onClick={() => setViewMode("list")}
								className="h-7 px-2"
							>
								<List className="w-3 h-3" />
							</Button>
						</div>
					</div>
				</div>

				{searchQuery && (
					<div className="text-sm text-gray-600">
						{t("providerGrid.search.results", {
							count: filteredAndSortedProviders.length,
							query: searchQuery,
						})}
					</div>
				)}
			</div>

			{/* Grille de providers */}
			<div className="space-y-4">
				{filteredAndSortedProviders.length === 0 ? (
					<div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
						<div className="space-y-3">
							<div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
								<Search className="w-6 h-6 text-gray-400" />
							</div>
							<div>
								<h3 className="font-medium text-gray-900">
									{searchQuery || filterStatus !== "all"
										? t("providerGrid.search.noResults")
										: t("providerGrid.search.noProviders")}
								</h3>
								<p className="text-sm text-gray-600 mt-1">
									{searchQuery || filterStatus !== "all"
										? t("providerGrid.search.adjustCriteria")
										: t("providerGrid.search.addFirst")}
								</p>
							</div>
							{onAddProvider && !searchQuery && filterStatus === "all" && (
								<Button onClick={onAddProvider} size="sm">
									<Plus className="w-4 h-4 mr-2" />
									{t("providerGrid.search.addFirstButton")}
								</Button>
							)}
						</div>
					</div>
				) : (
					<div
						className={cn(
							"grid gap-4",
							viewMode === "grid"
								? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
								: "grid-cols-1 max-w-2xl mx-auto",
						)}
					>
						{filteredAndSortedProviders.map((provider) => (
							<ThemedProviderCard
								key={provider.id}
								provider={provider}
								onConfigure={onConfigure}
								onTest={onTest}
								onToggle={onToggle}
								onRemove={onRemove}
								className={viewMode === "list" ? "max-w-2xl" : ""}
							/>
						))}
					</div>
				)}
			</div>
		</div>
	);
}
