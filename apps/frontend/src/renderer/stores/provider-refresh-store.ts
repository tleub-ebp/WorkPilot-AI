import { create } from 'zustand';

interface ProviderRefreshState {
  lastRefresh: number;
  triggerRefresh: () => void;
}

export const useProviderRefreshStore = create<ProviderRefreshState>((set) => ({
  lastRefresh: Date.now(),
  triggerRefresh: () => set({ lastRefresh: Date.now() })
}));
