/**
 * @deprecated — Thin backward-compatible wrapper around the unified auth-store.
 * Import from '../stores/auth-store' for new code.
 */

import type { RateLimitInfo, SDKRateLimitInfo } from "../../shared/types";
import { useAuthStore } from "./auth-store";

interface RateLimitState {
	isModalOpen: boolean;
	rateLimitInfo: RateLimitInfo | null;
	isSDKModalOpen: boolean;
	sdkRateLimitInfo: SDKRateLimitInfo | null;
	hasPendingRateLimit: boolean;
	pendingRateLimitType: "terminal" | "sdk" | null;
	showRateLimitModal: (info: RateLimitInfo) => void;
	hideRateLimitModal: () => void;
	showSDKRateLimitModal: (info: SDKRateLimitInfo) => void;
	hideSDKRateLimitModal: () => void;
	reopenRateLimitModal: () => void;
	clearPendingRateLimit: () => void;
}

function mapState(): RateLimitState {
	const s = useAuthStore.getState();
	return {
		isModalOpen: s.rateLimit_isModalOpen,
		rateLimitInfo: s.rateLimit_info,
		isSDKModalOpen: s.rateLimit_isSDKModalOpen,
		sdkRateLimitInfo: s.rateLimit_sdkInfo,
		hasPendingRateLimit: s.rateLimit_hasPending,
		pendingRateLimitType: s.rateLimit_pendingType,
		showRateLimitModal: s.rateLimit_showModal,
		hideRateLimitModal: s.rateLimit_hideModal,
		showSDKRateLimitModal: s.rateLimit_showSDKModal,
		hideSDKRateLimitModal: s.rateLimit_hideSDKModal,
		reopenRateLimitModal: s.rateLimit_reopenModal,
		clearPendingRateLimit: s.rateLimit_clearPending,
	};
}

export const useRateLimitStore = (): RateLimitState => {
	const store = useAuthStore();
	return {
		isModalOpen: store.rateLimit_isModalOpen,
		rateLimitInfo: store.rateLimit_info,
		isSDKModalOpen: store.rateLimit_isSDKModalOpen,
		sdkRateLimitInfo: store.rateLimit_sdkInfo,
		hasPendingRateLimit: store.rateLimit_hasPending,
		pendingRateLimitType: store.rateLimit_pendingType,
		showRateLimitModal: store.rateLimit_showModal,
		hideRateLimitModal: store.rateLimit_hideModal,
		showSDKRateLimitModal: store.rateLimit_showSDKModal,
		hideSDKRateLimitModal: store.rateLimit_hideSDKModal,
		reopenRateLimitModal: store.rateLimit_reopenModal,
		clearPendingRateLimit: store.rateLimit_clearPending,
	};
};

// Expose getState() for non-React access (e.g. in useIpc.ts)
useRateLimitStore.getState = mapState;
