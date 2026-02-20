/**
 * @deprecated — Thin backward-compatible wrapper around the unified auth-store.
 * Import from '../stores/auth-store' for new code.
 */
import { useAuthStore } from './auth-store';

interface ProviderRefreshState {
  lastRefresh: number;
  triggerRefresh: () => void;
}

export const useProviderRefreshStore = (): ProviderRefreshState => {
  const store = useAuthStore();
  return {
    lastRefresh: store.providerRefresh_lastRefresh,
    triggerRefresh: store.providerRefresh_trigger,
  };
};

// Expose getState() for non-React access
useProviderRefreshStore.getState = () => {
  const s = useAuthStore.getState();
  return {
    lastRefresh: s.providerRefresh_lastRefresh,
    triggerRefresh: s.providerRefresh_trigger,
  };
};
