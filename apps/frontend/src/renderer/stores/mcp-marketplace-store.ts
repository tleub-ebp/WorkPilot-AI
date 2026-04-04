/**
 * MCP Marketplace Store
 *
 * Zustand store for the MCP Marketplace feature.
 * Manages catalog browsing, installed servers, and builder projects.
 */

import { create } from "zustand";
import type {
	McpBuilderProject,
	McpInstalledServer,
	McpMarketplaceFilters,
	McpMarketplaceServer,
	McpMarketplaceTab,
} from "../../shared/types/mcp-marketplace";

interface McpMarketplaceState {
	// UI state
	activeTab: McpMarketplaceTab;
	filters: McpMarketplaceFilters;
	selectedServerId: string | null;
	isInstalling: string | null;

	// Data
	catalog: McpMarketplaceServer[];
	installed: McpInstalledServer[];
	builderProjects: McpBuilderProject[];

	// Loading
	isCatalogLoading: boolean;
	isInstalledLoading: boolean;
	isBuilderLoading: boolean;
	error: string | null;

	// Actions - UI
	setActiveTab: (tab: McpMarketplaceTab) => void;
	setFilters: (filters: Partial<McpMarketplaceFilters>) => void;
	setSelectedServer: (serverId: string | null) => void;

	// Actions - Data
	setCatalog: (catalog: McpMarketplaceServer[]) => void;
	setInstalled: (installed: McpInstalledServer[]) => void;
	setBuilderProjects: (projects: McpBuilderProject[]) => void;
	addInstalledServer: (server: McpInstalledServer) => void;
	removeInstalledServer: (serverId: string) => void;
	updateInstalledServer: (
		serverId: string,
		updates: Partial<McpInstalledServer>,
	) => void;
	addBuilderProject: (project: McpBuilderProject) => void;
	updateBuilderProject: (
		projectId: string,
		updates: Partial<McpBuilderProject>,
	) => void;
	removeBuilderProject: (projectId: string) => void;

	// Actions - Loading
	setIsInstalling: (serverId: string | null) => void;
	setCatalogLoading: (loading: boolean) => void;
	setInstalledLoading: (loading: boolean) => void;
	setBuilderLoading: (loading: boolean) => void;
	setError: (error: string | null) => void;

	// Computed helpers
	getFilteredCatalog: () => McpMarketplaceServer[];
	isServerInstalled: (serverId: string) => boolean;
	getInstalledServer: (serverId: string) => McpInstalledServer | undefined;
}

const defaultFilters: McpMarketplaceFilters = {
	search: "",
	category: "all",
	sortBy: "popular",
	showInstalledOnly: false,
	showVerifiedOnly: false,
};

export const useMcpMarketplaceStore = create<McpMarketplaceState>(
	(set, get) => ({
		// Initial state
		activeTab: "catalog",
		filters: { ...defaultFilters },
		selectedServerId: null,
		isInstalling: null,
		catalog: [],
		installed: [],
		builderProjects: [],
		isCatalogLoading: false,
		isInstalledLoading: false,
		isBuilderLoading: false,
		error: null,

		// UI Actions
		setActiveTab: (tab) => set({ activeTab: tab }),

		setFilters: (updates) =>
			set((state) => ({
				filters: { ...state.filters, ...updates },
			})),

		setSelectedServer: (serverId) => set({ selectedServerId: serverId }),

		// Data Actions
		setCatalog: (catalog) => set({ catalog }),

		setInstalled: (installed) => set({ installed }),

		setBuilderProjects: (projects) => set({ builderProjects: projects }),

		addInstalledServer: (server) =>
			set((state) => ({
				installed: [...state.installed, server],
			})),

		removeInstalledServer: (serverId) =>
			set((state) => ({
				installed: state.installed.filter((s) => s.serverId !== serverId),
			})),

		updateInstalledServer: (serverId, updates) =>
			set((state) => ({
				installed: state.installed.map((s) =>
					s.serverId === serverId ? { ...s, ...updates } : s,
				),
			})),

		addBuilderProject: (project) =>
			set((state) => ({
				builderProjects: [...state.builderProjects, project],
			})),

		updateBuilderProject: (projectId, updates) =>
			set((state) => ({
				builderProjects: state.builderProjects.map((p) =>
					p.id === projectId ? { ...p, ...updates } : p,
				),
			})),

		removeBuilderProject: (projectId) =>
			set((state) => ({
				builderProjects: state.builderProjects.filter(
					(p) => p.id !== projectId,
				),
			})),

		// Loading Actions
		setIsInstalling: (serverId) => set({ isInstalling: serverId }),
		setCatalogLoading: (loading) => set({ isCatalogLoading: loading }),
		setInstalledLoading: (loading) => set({ isInstalledLoading: loading }),
		setBuilderLoading: (loading) => set({ isBuilderLoading: loading }),
		setError: (error) => set({ error }),

		// Computed helpers
		getFilteredCatalog: () => {
			const { catalog, installed, filters } = get();
			let filtered = [...catalog];

			// Search
			if (filters.search) {
				const query = filters.search.toLowerCase();
				filtered = filtered.filter(
					(s) =>
						s.name.toLowerCase().includes(query) ||
						s.tagline.toLowerCase().includes(query) ||
						s.description.toLowerCase().includes(query) ||
						s.tags.some((t) => t.toLowerCase().includes(query)),
				);
			}

			// Category
			if (filters.category !== "all") {
				filtered = filtered.filter((s) => s.category === filters.category);
			}

			// Installed only
			if (filters.showInstalledOnly) {
				const installedIds = new Set(installed.map((i) => i.serverId));
				filtered = filtered.filter((s) => installedIds.has(s.id));
			}

			// Verified only
			if (filters.showVerifiedOnly) {
				filtered = filtered.filter((s) => s.verified);
			}

			// Sort
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

		isServerInstalled: (serverId) => {
			return get().installed.some((s) => s.serverId === serverId);
		},

		getInstalledServer: (serverId) => {
			return get().installed.find((s) => s.serverId === serverId);
		},
	}),
);

// ============================================
// Async action helpers (called from components)
// ============================================

export async function loadMarketplaceCatalog(): Promise<void> {
	const store = useMcpMarketplaceStore.getState();
	store.setCatalogLoading(true);
	store.setError(null);

	try {
		const result = await globalThis.electronAPI?.invoke(
			"mcpMarketplace:getCatalog",
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

export async function loadInstalledServers(): Promise<void> {
	const store = useMcpMarketplaceStore.getState();
	store.setInstalledLoading(true);

	try {
		const result = await globalThis.electronAPI?.invoke(
			"mcpMarketplace:getInstalled",
		);
		if (result?.success) {
			store.setInstalled(result.data);
		}
	} catch (err) {
		console.error("[MCP Marketplace] Failed to load installed servers:", err);
	} finally {
		store.setInstalledLoading(false);
	}
}

export async function installMarketplaceServer(
	serverId: string,
	envVars: Record<string, string> = {},
): Promise<boolean> {
	const store = useMcpMarketplaceStore.getState();
	store.setIsInstalling(serverId);

	try {
		const result = await globalThis.electronAPI?.invoke(
			"mcpMarketplace:install",
			{ serverId, envVars },
		);
		if (result?.success) {
			store.addInstalledServer(result.data);
			store.setIsInstalling(null);
			return true;
		} else {
			store.setError(result?.error || "Installation failed");
			store.setIsInstalling(null);
			return false;
		}
	} catch (err) {
		store.setError(err instanceof Error ? err.message : "Installation failed");
		store.setIsInstalling(null);
		return false;
	}
}

export async function uninstallMarketplaceServer(
	serverId: string,
): Promise<boolean> {
	const store = useMcpMarketplaceStore.getState();

	try {
		const result = await globalThis.electronAPI?.invoke(
			"mcpMarketplace:uninstall",
			{ serverId },
		);
		if (result?.success) {
			store.removeInstalledServer(serverId);
			return true;
		}
		return false;
	} catch {
		return false;
	}
}

export async function toggleMarketplaceServer(
	serverId: string,
	enabled: boolean,
): Promise<void> {
	const store = useMcpMarketplaceStore.getState();

	try {
		await globalThis.electronAPI?.invoke("mcpMarketplace:toggleServer", {
			serverId,
			enabled,
		});
		store.updateInstalledServer(serverId, { enabled });
	} catch (err) {
		console.error("[MCP Marketplace] Failed to toggle server:", err);
	}
}

export async function loadBuilderProjects(): Promise<void> {
	const store = useMcpMarketplaceStore.getState();
	store.setBuilderLoading(true);

	try {
		const result = await globalThis.electronAPI?.invoke(
			"mcpMarketplace:getBuilderProjects",
		);
		if (result?.success) {
			store.setBuilderProjects(result.data);
		}
	} catch (err) {
		console.error("[MCP Marketplace] Failed to load builder projects:", err);
	} finally {
		store.setBuilderLoading(false);
	}
}

export async function saveBuilderProject(
	project: McpBuilderProject,
): Promise<boolean> {
	const store = useMcpMarketplaceStore.getState();

	try {
		const result = await globalThis.electronAPI?.invoke(
			"mcpMarketplace:saveBuilder",
			project,
		);
		if (result?.success) {
			const existing = store.builderProjects.find((p) => p.id === project.id);
			if (existing) {
				store.updateBuilderProject(project.id, project);
			} else {
				store.addBuilderProject(project);
			}
			return true;
		}
		return false;
	} catch {
		return false;
	}
}

export async function deleteBuilderProject(
	projectId: string,
): Promise<boolean> {
	const store = useMcpMarketplaceStore.getState();

	try {
		const result = await globalThis.electronAPI?.invoke(
			"mcpMarketplace:deleteBuilder",
			{ projectId },
		);
		if (result?.success) {
			store.removeBuilderProject(projectId);
			return true;
		}
		return false;
	} catch {
		return false;
	}
}
