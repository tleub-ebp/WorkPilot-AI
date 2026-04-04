/**
 * Plugin Marketplace Store
 *
 * Zustand store for the Plugin Marketplace feature.
 */

import { create } from "zustand";
import type {
	InstalledPlugin,
	MarketplacePlugin,
	PluginMarketplaceFilters,
	PluginMarketplaceTab,
} from "../../shared/types/plugin-marketplace";

interface PluginMarketplaceState {
	// UI state
	activeTab: PluginMarketplaceTab;
	filters: PluginMarketplaceFilters;
	selectedPluginId: string | null;
	isInstalling: string | null;

	// Data
	catalog: MarketplacePlugin[];
	installed: InstalledPlugin[];

	// Loading
	isCatalogLoading: boolean;
	isInstalledLoading: boolean;
	error: string | null;

	// Actions - UI
	setActiveTab: (tab: PluginMarketplaceTab) => void;
	setFilters: (filters: Partial<PluginMarketplaceFilters>) => void;
	setSelectedPlugin: (pluginId: string | null) => void;

	// Actions - Data
	setCatalog: (catalog: MarketplacePlugin[]) => void;
	setInstalled: (installed: InstalledPlugin[]) => void;
	addInstalledPlugin: (plugin: InstalledPlugin) => void;
	removeInstalledPlugin: (pluginId: string) => void;
	updateInstalledPlugin: (
		pluginId: string,
		updates: Partial<InstalledPlugin>,
	) => void;

	// Actions - Loading
	setIsInstalling: (pluginId: string | null) => void;
	setCatalogLoading: (loading: boolean) => void;
	setInstalledLoading: (loading: boolean) => void;
	setError: (error: string | null) => void;

	// Computed helpers
	getFilteredCatalog: () => MarketplacePlugin[];
	isPluginInstalled: (pluginId: string) => boolean;
	getInstalledPlugin: (pluginId: string) => InstalledPlugin | undefined;
}

const defaultFilters: PluginMarketplaceFilters = {
	search: "",
	type: "all",
	sortBy: "popular",
	showInstalledOnly: false,
	showVerifiedOnly: false,
};

export const usePluginMarketplaceStore = create<PluginMarketplaceState>(
	(set, get) => ({
		// Initial state
		activeTab: "catalog",
		filters: { ...defaultFilters },
		selectedPluginId: null,
		isInstalling: null,
		catalog: [],
		installed: [],
		isCatalogLoading: false,
		isInstalledLoading: false,
		error: null,

		// UI Actions
		setActiveTab: (tab) => set({ activeTab: tab }),
		setFilters: (updates) =>
			set((state) => ({ filters: { ...state.filters, ...updates } })),
		setSelectedPlugin: (pluginId) => set({ selectedPluginId: pluginId }),

		// Data Actions
		setCatalog: (catalog) => set({ catalog }),
		setInstalled: (installed) => set({ installed }),

		addInstalledPlugin: (plugin) =>
			set((state) => ({ installed: [...state.installed, plugin] })),

		removeInstalledPlugin: (pluginId) =>
			set((state) => ({
				installed: state.installed.filter((p) => p.pluginId !== pluginId),
			})),

		updateInstalledPlugin: (pluginId, updates) =>
			set((state) => ({
				installed: state.installed.map((p) =>
					p.pluginId === pluginId ? { ...p, ...updates } : p,
				),
			})),

		// Loading Actions
		setIsInstalling: (pluginId) => set({ isInstalling: pluginId }),
		setCatalogLoading: (loading) => set({ isCatalogLoading: loading }),
		setInstalledLoading: (loading) => set({ isInstalledLoading: loading }),
		setError: (error) => set({ error }),

		// Computed helpers
		getFilteredCatalog: () => {
			const { catalog, installed, filters } = get();
			let filtered = [...catalog];

			if (filters.search) {
				const query = filters.search.toLowerCase();
				filtered = filtered.filter(
					(p) =>
						p.name.toLowerCase().includes(query) ||
						p.tagline.toLowerCase().includes(query) ||
						p.description.toLowerCase().includes(query) ||
						p.tags.some((t) => t.toLowerCase().includes(query)),
				);
			}

			if (filters.type !== "all") {
				filtered = filtered.filter((p) => p.type === filters.type);
			}

			if (filters.showInstalledOnly) {
				const installedIds = new Set(installed.map((i) => i.pluginId));
				filtered = filtered.filter((p) => installedIds.has(p.id));
			}

			if (filters.showVerifiedOnly) {
				filtered = filtered.filter((p) => p.verified);
			}

			switch (filters.sortBy) {
				case "popular":
					filtered.sort((a, b) => b.downloads - a.downloads);
					break;
				case "rating":
					filtered.sort((a, b) => b.rating - a.rating);
					break;
				case "newest":
					filtered.sort(
						(a, b) =>
							new Date(b.addedAt).getTime() - new Date(a.addedAt).getTime(),
					);
					break;
				case "name":
					filtered.sort((a, b) => a.name.localeCompare(b.name));
					break;
			}

			return filtered;
		},

		isPluginInstalled: (pluginId) =>
			get().installed.some((p) => p.pluginId === pluginId),
		getInstalledPlugin: (pluginId) =>
			get().installed.find((p) => p.pluginId === pluginId),
	}),
);

// ============================================
// Async action helpers
// ============================================

export async function loadPluginCatalog(): Promise<void> {
	const store = usePluginMarketplaceStore.getState();
	store.setCatalogLoading(true);
	store.setError(null);
	try {
		const result = await globalThis.electronAPI?.invoke(
			"pluginMarketplace:getCatalog",
		);
		if (result?.success) {
			store.setCatalog(result.data);
		} else {
			store.setError(result?.error || "Failed to load catalog");
		}
	} catch (err) {
		store.setError(
			err instanceof Error ? err.message : "Failed to load catalog",
		);
	} finally {
		store.setCatalogLoading(false);
	}
}

export async function loadInstalledPlugins(): Promise<void> {
	const store = usePluginMarketplaceStore.getState();
	store.setInstalledLoading(true);
	try {
		const result = await globalThis.electronAPI?.invoke(
			"pluginMarketplace:getInstalled",
		);
		if (result?.success) {
			store.setInstalled(result.data);
		}
	} catch (err) {
		console.error(
			"[Plugin Marketplace] Failed to load installed plugins:",
			err,
		);
	} finally {
		store.setInstalledLoading(false);
	}
}

export async function installPlugin(
	pluginId: string,
	config?: Record<string, string>,
): Promise<boolean> {
	const store = usePluginMarketplaceStore.getState();
	store.setIsInstalling(pluginId);
	try {
		const result = await globalThis.electronAPI?.invoke(
			"pluginMarketplace:install",
			{
				pluginId,
				config,
			},
		);
		if (result?.success) {
			store.addInstalledPlugin(result.data);
			return true;
		}
		store.setError(result?.error || "Installation failed");
		return false;
	} catch (err) {
		store.setError(err instanceof Error ? err.message : "Installation failed");
		return false;
	} finally {
		store.setIsInstalling(null);
	}
}

export async function uninstallPlugin(pluginId: string): Promise<boolean> {
	try {
		const result = await globalThis.electronAPI?.invoke(
			"pluginMarketplace:uninstall",
			{
				pluginId,
			},
		);
		if (result?.success) {
			usePluginMarketplaceStore.getState().removeInstalledPlugin(pluginId);
			return true;
		}
		return false;
	} catch {
		return false;
	}
}

export async function togglePlugin(
	pluginId: string,
	enabled: boolean,
): Promise<void> {
	try {
		await globalThis.electronAPI?.invoke("pluginMarketplace:toggle", {
			pluginId,
			enabled,
		});
		usePluginMarketplaceStore
			.getState()
			.updateInstalledPlugin(pluginId, { enabled });
	} catch (err) {
		console.error("[Plugin Marketplace] Failed to toggle plugin:", err);
	}
}
