/**
 * @deprecated — Thin backward-compatible wrapper around the unified auth-store.
 * Import from '../stores/auth-store' for new code.
 */
import { useAuthStore } from './auth-store';
import type { AuthFailureInfo } from '../../shared/types';

interface AuthFailureState {
  isModalOpen: boolean;
  authFailureInfo: AuthFailureInfo | null;
  hasPendingAuthFailure: boolean;
  showAuthFailureModal: (info: AuthFailureInfo) => void;
  hideAuthFailureModal: () => void;
  clearAuthFailure: () => void;
}

export const useAuthFailureStore = (): AuthFailureState => {
  const store = useAuthStore();
  return {
    isModalOpen: store.authFailure_isModalOpen,
    authFailureInfo: store.authFailure_info,
    hasPendingAuthFailure: store.authFailure_hasPending,
    showAuthFailureModal: store.authFailure_show,
    hideAuthFailureModal: store.authFailure_hide,
    clearAuthFailure: store.authFailure_clear,
  };
};

// Expose getState() for non-React access (e.g. in useIpc.ts)
useAuthFailureStore.getState = () => {
  const s = useAuthStore.getState();
  return {
    isModalOpen: s.authFailure_isModalOpen,
    authFailureInfo: s.authFailure_info,
    hasPendingAuthFailure: s.authFailure_hasPending,
    showAuthFailureModal: s.authFailure_show,
    hideAuthFailureModal: s.authFailure_hide,
    clearAuthFailure: s.authFailure_clear,
  };
};
