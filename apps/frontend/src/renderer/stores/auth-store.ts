/**
 * Unified Auth Store — consolidates auth-failure, rate-limit, and provider-refresh
 * into a single Zustand store with logical slices.
 *
 * Architecture improvement 3.2: Micro-stores regrouped by domain.
 * Replaces:
 *   - auth-failure-store.ts
 *   - rate-limit-store.ts
 *   - provider-refresh-store.ts
 *
 * All property names are prefixed by slice to avoid collisions
 * (e.g. authFailure_isModalOpen vs rateLimit_isModalOpen).
 * The old store files are kept as thin wrappers that map back to the
 * original property names for backward compatibility.
 */
import { create } from 'zustand';
import type { RateLimitInfo, SDKRateLimitInfo, AuthFailureInfo } from '../../shared/types';

// ============================================
// Slice interfaces (prefixed to avoid collisions)
// ============================================

export interface AuthFailureSlice {
  authFailure_isModalOpen: boolean;
  authFailure_info: AuthFailureInfo | null;
  authFailure_hasPending: boolean;
  authFailure_show: (info: AuthFailureInfo) => void;
  authFailure_hide: () => void;
  authFailure_clear: () => void;
}

export interface RateLimitSlice {
  rateLimit_isModalOpen: boolean;
  rateLimit_info: RateLimitInfo | null;
  rateLimit_isSDKModalOpen: boolean;
  rateLimit_sdkInfo: SDKRateLimitInfo | null;
  rateLimit_hasPending: boolean;
  rateLimit_pendingType: 'terminal' | 'sdk' | null;
  rateLimit_showModal: (info: RateLimitInfo) => void;
  rateLimit_hideModal: () => void;
  rateLimit_showSDKModal: (info: SDKRateLimitInfo) => void;
  rateLimit_hideSDKModal: () => void;
  rateLimit_reopenModal: () => void;
  rateLimit_clearPending: () => void;
}

export interface ProviderRefreshSlice {
  providerRefresh_lastRefresh: number;
  providerRefresh_trigger: () => void;
}

// ============================================
// Combined store type
// ============================================

export type AuthStoreState = AuthFailureSlice & RateLimitSlice & ProviderRefreshSlice;

// ============================================
// Store implementation
// ============================================

export const useAuthStore = create<AuthStoreState>((set, get) => ({
  // --- Auth Failure slice ---
  authFailure_isModalOpen: false,
  authFailure_info: null,
  authFailure_hasPending: false,

  authFailure_show: (info: AuthFailureInfo) => {
    set({
      authFailure_isModalOpen: true,
      authFailure_info: info,
      authFailure_hasPending: true,
    });
  },

  authFailure_hide: () => {
    set({ authFailure_isModalOpen: false });
  },

  authFailure_clear: () => {
    set({
      authFailure_isModalOpen: false,
      authFailure_info: null,
      authFailure_hasPending: false,
    });
  },

  // --- Rate Limit slice ---
  rateLimit_isModalOpen: false,
  rateLimit_info: null,
  rateLimit_isSDKModalOpen: false,
  rateLimit_sdkInfo: null,
  rateLimit_hasPending: false,
  rateLimit_pendingType: null,

  rateLimit_showModal: (info: RateLimitInfo) => {
    set({
      rateLimit_isModalOpen: true,
      rateLimit_info: info,
      rateLimit_hasPending: true,
      rateLimit_pendingType: 'terminal'
    });
  },

  rateLimit_hideModal: () => {
    set({ rateLimit_isModalOpen: false });
  },

  rateLimit_showSDKModal: (info: SDKRateLimitInfo) => {
    set({
      rateLimit_isSDKModalOpen: true,
      rateLimit_sdkInfo: info,
      rateLimit_hasPending: true,
      rateLimit_pendingType: 'sdk'
    });
  },

  rateLimit_hideSDKModal: () => {
    set({ rateLimit_isSDKModalOpen: false });
  },

  rateLimit_reopenModal: () => {
    const state = get();
    if (state.rateLimit_pendingType === 'terminal' && state.rateLimit_info) {
      set({ rateLimit_isModalOpen: true });
    } else if (state.rateLimit_pendingType === 'sdk' && state.rateLimit_sdkInfo) {
      set({ rateLimit_isSDKModalOpen: true });
    }
  },

  rateLimit_clearPending: () => {
    set({
      rateLimit_hasPending: false,
      rateLimit_pendingType: null,
      rateLimit_info: null,
      rateLimit_sdkInfo: null
    });
  },

  // --- Provider Refresh slice ---
  providerRefresh_lastRefresh: Date.now(),
  providerRefresh_trigger: () => set({ providerRefresh_lastRefresh: Date.now() })
}));
