import { Filter, Grid3x3, List, Plus, RefreshCw, Search } from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { ProviderCard } from "./ProviderCard";

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
	icon?: React.ElementType;
}

interface ProviderGridProps {
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

export function ProviderGrid({
	providers,
	onConfigure,
	onTest,
	onToggle,
	onRemove,
	onAddProvider,
	onRefreshProviders,
	isLoading = false,
	className,
}: ProviderGridProps) {
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
			{/* En-tête avec statistiques */}
			<div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold text-foreground">
						{t("providerGrid.title")}
					</h2>
					<div className="flex gap-2 mt-2">
						<Badge variant="secondary">
							{t("providerGrid.stats.total", { count: stats.total })}
						</Badge>
						<Badge className="bg-green-100 text-green-800 border-green-200">
							{t("providerGrid.stats.configured", { count: stats.configured })}
						</Badge>
						{stats.errors > 0 && (
							<Badge variant="destructive">
								{t("providerGrid.stats.errors", { count: stats.errors })}
							</Badge>
						)}
					</div>
				</div>

				<div className="flex gap-2">
					{onRefreshProviders && (
						<Button
							variant="outline"
							onClick={onRefreshProviders}
							disabled={isLoading}
							className="flex items-center gap-2"
						>
							<RefreshCw
								className={cn("w-4 h-4", isLoading && "animate-spin")}
							/>
							Actualiser
						</Button>
					)}
					{onAddProvider && (
						<Button onClick={onAddProvider} className="flex items-center gap-2">
							<Plus className="w-4 h-4" />
							Ajouter un provider
						</Button>
					)}
				</div>
			</div>

			{/* Barre de recherche et filtres */}
			<div className="flex flex-col lg:flex-row gap-4">
				<div className="flex-1">
					<div className="relative">
						<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
						<Input
							placeholder="Rechercher un provider..."
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							className="pl-10"
						/>
					</div>
				</div>

				<div className="flex gap-2">
					<Select
						value={filterStatus}
						onValueChange={(value: FilterStatus) => setFilterStatus(value)}
					>
						<SelectTrigger className="w-40">
							<Filter className="w-4 h-4 mr-2" />
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="all">Tous</SelectItem>
							<SelectItem value="configured">Configurés</SelectItem>
							<SelectItem value="unconfigured">Non configurés</SelectItem>
							<SelectItem value="errors">Avec erreurs</SelectItem>
						</SelectContent>
					</Select>

					<Select
						value={sortBy}
						onValueChange={(value: SortBy) => setSortBy(value)}
					>
						<SelectTrigger className="w-44">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value="name">Nom</SelectItem>
							<SelectItem value="category">Catégorie</SelectItem>
							<SelectItem value="status">Statut</SelectItem>
							<SelectItem value="usage">Utilisation</SelectItem>
						</SelectContent>
					</Select>

					<div className="flex border rounded-md">
						<Button
							variant={viewMode === "grid" ? "default" : "ghost"}
							size="sm"
							onClick={() => setViewMode("grid")}
							className="rounded-r-none"
						>
							<Grid3x3 className="w-4 h-4" />
						</Button>
						<Button
							variant={viewMode === "list" ? "default" : "ghost"}
							size="sm"
							onClick={() => setViewMode("list")}
							className="rounded-l-none"
						>
							<List className="w-4 h-4" />
						</Button>
					</div>
				</div>
			</div>

			{/* Résultats */}
			<div>
				{searchQuery && (
					<p className="text-sm text-muted-foreground mb-4">
						{filteredAndSortedProviders.length} résultat
						{filteredAndSortedProviders.length > 1 ? "s" : ""} pour "
						{searchQuery}"
					</p>
				)}

				{filteredAndSortedProviders.length === 0 ? (
					<div className="text-center py-12">
						<div className="text-muted-foreground">
							{searchQuery || filterStatus !== "all"
								? "Aucun provider ne correspond à vos critères de recherche."
								: "Aucun provider disponible."}
						</div>
						{onAddProvider && !searchQuery && filterStatus === "all" && (
							<Button onClick={onAddProvider} className="mt-4">
								Ajouter votre premier provider
							</Button>
						)}
					</div>
				) : (
					<div
						className={cn(
							viewMode === "grid"
								? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
								: "space-y-4",
						)}
					>
						{filteredAndSortedProviders.map((provider) => (
							<ProviderCard
								key={provider.id}
								provider={provider}
								onConfigure={onConfigure}
								onTest={onTest}
								onToggle={onToggle}
								onRemove={onRemove}
								className={viewMode === "list" ? "max-w-4xl" : ""}
							/>
						))}
					</div>
				)}
			</div>
		</div>
	);
}
