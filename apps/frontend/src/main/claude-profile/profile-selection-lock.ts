/**
 * Profile Selection Lock Module
 * Prevents race conditions where multiple concurrent operations select
 * the same "best" profile simultaneously, overloading it.
 *
 * Uses a simple in-memory lock with auto-release timeout as safety net.
 */

// ============================================
// Constants
// ============================================

/** Auto-release timeout for stale locks (30 seconds) */
const LOCK_TIMEOUT_MS = 30_000;

// ============================================
// Types
// ============================================

interface LockEntry {
	acquiredAt: number;
	acquiredBy: string;
}

// ============================================
// ProfileSelectionLock
// ============================================

/**
 * Singleton lock manager for profile selection.
 * Ensures that when one operation is switching to a profile,
 * other operations skip that profile and pick the next-best one.
 */
class ProfileSelectionLock {
	private static instance: ProfileSelectionLock;

	/** Map of profileId → lock entry */
	private pendingSelections: Map<string, LockEntry> = new Map();

	private constructor() {}

	static getInstance(): ProfileSelectionLock {
		if (!ProfileSelectionLock.instance) {
			ProfileSelectionLock.instance = new ProfileSelectionLock();
		}
		return ProfileSelectionLock.instance;
	}

	/**
	 * Try to acquire a selection lock for a profile.
	 * @param profileId - Profile ID to lock
	 * @param acquiredBy - Identifier of the caller (task ID, 'proactive-swap', etc.)
	 * @returns true if the lock was acquired, false if the profile is already locked
	 */
	tryAcquire(profileId: string, acquiredBy: string): boolean {
		this.pruneExpired();

		if (this.pendingSelections.has(profileId)) {
			return false;
		}

		this.pendingSelections.set(profileId, {
			acquiredAt: Date.now(),
			acquiredBy,
		});
		return true;
	}

	/**
	 * Release a selection lock for a profile.
	 * Should be called after the swap completes or fails.
	 */
	release(profileId: string): void {
		this.pendingSelections.delete(profileId);
	}

	/**
	 * Check if a profile is currently locked by another selection.
	 */
	isLocked(profileId: string): boolean {
		this.pruneExpired();
		return this.pendingSelections.has(profileId);
	}

	/**
	 * Get the set of currently locked profile IDs.
	 * Used by getBestAvailableProfile() to exclude locked profiles from candidates.
	 */
	getLockedProfileIds(): Set<string> {
		this.pruneExpired();
		return new Set(this.pendingSelections.keys());
	}

	/**
	 * Clear all locks (for testing or reset).
	 */
	clear(): void {
		this.pendingSelections.clear();
	}

	/**
	 * Remove expired locks (safety net against leaked locks).
	 */
	private pruneExpired(): void {
		const now = Date.now();
		for (const [id, lock] of this.pendingSelections) {
			if (now - lock.acquiredAt > LOCK_TIMEOUT_MS) {
				this.pendingSelections.delete(id);
			}
		}
	}
}

// ============================================
// Exports
// ============================================

/**
 * Get the singleton ProfileSelectionLock instance.
 */
export function getProfileSelectionLock(): ProfileSelectionLock {
	return ProfileSelectionLock.getInstance();
}

/**
 * Reset the lock (for testing).
 */
export function resetProfileSelectionLock(): void {
	ProfileSelectionLock.getInstance().clear();
}
