import { create } from "zustand";

export type PruneStrategy = "lru" | "oldest" | "duplicates";

export interface MemoryStatus {
	episode_count: number;
	disk_usage_bytes: number;
	oldest_episode: string | null;
	newest_episode: string | null;
	graphiti_enabled: boolean;
	retention_days: number;
	max_episodes: number;
	prune_strategy: PruneStrategy;
	auto_prune: boolean;
}

export interface MemoryEpisode {
	id: string;
	created_at?: string;
	content?: string;
	source?: string;
	[key: string]: unknown;
}

interface MemoryLifecycleState {
	status: MemoryStatus | null;
	episodes: MemoryEpisode[];
	totalEpisodes: number;
	isLoading: boolean;
	isPruning: boolean;
	error: string | null;

	loadStatus: (projectDir: string) => Promise<void>;
	loadEpisodes: (
		projectDir: string,
		page?: number,
		pageSize?: number,
	) => Promise<void>;
	runPrune: (
		projectDir: string,
		options?: {
			strategy?: PruneStrategy;
			maxAgeDays?: number;
			maxCount?: number;
			dryRun?: boolean;
		},
	) => Promise<{ pruned: number; remaining: number } | null>;
	setPolicy: (
		projectDir: string,
		policy: Partial<
			Pick<
				MemoryStatus,
				"retention_days" | "max_episodes" | "prune_strategy" | "auto_prune"
			>
		>,
	) => Promise<void>;
	deleteEpisode: (projectDir: string, episodeId: string) => Promise<void>;
	exportMemories: (
		projectDir: string,
		outputPath: string,
	) => Promise<{ count: number; path: string } | null>;
	clearError: () => void;
}

export const useMemoryLifecycleStore = create<MemoryLifecycleState>((set) => ({
	status: null,
	episodes: [],
	totalEpisodes: 0,
	isLoading: false,
	isPruning: false,
	error: null,

	loadStatus: async (projectDir) => {
		set({ isLoading: true, error: null });
		try {
			const result = await globalThis.electronAPI.invoke(
				"memoryLifecycle:getStatus",
				projectDir,
			);
			if (result.success) {
				set({ status: result.data as MemoryStatus });
			} else {
				set({ error: result.error ?? "Failed to load memory status" });
			}
		} catch (err) {
			set({ error: String(err) });
		} finally {
			set({ isLoading: false });
		}
	},

	loadEpisodes: async (projectDir, page = 0, pageSize = 50) => {
		set({ isLoading: true, error: null });
		try {
			const result = await globalThis.electronAPI.invoke(
				"memoryLifecycle:listMemories",
				projectDir,
				page,
				pageSize,
			);
			if (result.success) {
				const data = result.data as { items: MemoryEpisode[]; total: number };
				set({ episodes: data.items, totalEpisodes: data.total });
			} else {
				set({ error: result.error ?? "Failed to load episodes" });
			}
		} catch (err) {
			set({ error: String(err) });
		} finally {
			set({ isLoading: false });
		}
	},

	runPrune: async (projectDir, options = {}) => {
		set({ isPruning: true, error: null });
		try {
			const result = await globalThis.electronAPI.invoke(
				"memoryLifecycle:prune",
				projectDir,
				{
					strategy: options.strategy,
					max_age_days: options.maxAgeDays,
					max_count: options.maxCount,
					dry_run: options.dryRun,
				},
			);
			if (result.success) {
				return result.data as { pruned: number; remaining: number };
			}
			set({ error: result.error ?? "Prune failed" });
			return null;
		} catch (err) {
			set({ error: String(err) });
			return null;
		} finally {
			set({ isPruning: false });
		}
	},

	setPolicy: async (projectDir, policy) => {
		try {
			const mapped: Record<string, unknown> = {};
			if (policy.retention_days != null)
				mapped.retention_days = policy.retention_days;
			if (policy.max_episodes != null)
				mapped.max_episodes = policy.max_episodes;
			if (policy.prune_strategy != null)
				mapped.prune_strategy = policy.prune_strategy;
			if (policy.auto_prune != null) mapped.auto_prune = policy.auto_prune;
			await globalThis.electronAPI.invoke(
				"memoryLifecycle:setPolicy",
				projectDir,
				mapped,
			);
		} catch (err) {
			set({ error: String(err) });
		}
	},

	deleteEpisode: async (projectDir, episodeId) => {
		try {
			await globalThis.electronAPI.invoke(
				"memoryLifecycle:deleteMemory",
				projectDir,
				episodeId,
			);
			set((state) => ({
				episodes: state.episodes.filter((e) => e.id !== episodeId),
				totalEpisodes: Math.max(0, state.totalEpisodes - 1),
			}));
		} catch (err) {
			set({ error: String(err) });
		}
	},

	exportMemories: async (projectDir, outputPath) => {
		try {
			const result = await globalThis.electronAPI.invoke(
				"memoryLifecycle:export",
				projectDir,
				outputPath,
			);
			if (result.success) return result.data as { count: number; path: string };
			set({ error: result.error ?? "Export failed" });
			return null;
		} catch (err) {
			set({ error: String(err) });
			return null;
		}
	},

	clearError: () => set({ error: null }),
}));
