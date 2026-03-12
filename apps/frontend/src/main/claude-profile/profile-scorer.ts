/**
 * Profile Scorer Module
 * Handles profile availability scoring and auto-switch logic
 *
 * Priority-Based Selection (v3):
 * 1. User's configured priority order is the PRIMARY factor
 * 2. Accounts are filtered by availability criteria:
 *    - Must be authenticated
 *    - Must not be rate-limited (explicit 429 error)
 *    - Must be below user's configured thresholds (default: 95% session, 99% weekly)
 *    - Must not be locked by another concurrent selection (anti-race condition)
 * 3. First profile in priority order that passes all filters is selected
 * 4. If no profile passes all filters, falls back to "least bad" option
 *
 * Scoring considers:
 * - Authentication status, rate limit status, usage thresholds
 * - Remaining capacity and time-to-reset
 * - Consumption velocity (how fast usage is increasing)
 * - Reserved capacity from running operations
 */

import type { ClaudeProfile, ClaudeAutoSwitchSettings } from '../../shared/types';
import { isProfileRateLimited } from './rate-limit-manager';
import { isProfileAuthenticated } from './profile-utils';

const isDebug = process.env.DEBUG === 'true';

// ============================================
// Types
// ============================================

interface ScoredProfile {
  profile: ClaudeProfile;
  score: number;
  priorityIndex: number;
  isAvailable: boolean;
  unavailableReason?: string;
}

/**
 * Velocity data for a profile (from VelocityTracker)
 */
export interface VelocityData {
  sessionVelocity: number;  // % per minute (positive = increasing)
  weeklyVelocity: number;   // % per minute
  sampleCount: number;
  confidence: 'low' | 'medium' | 'high';
}

/**
 * Time-to-limit prediction (from VelocityTracker)
 */
export interface TimeToLimitData {
  sessionMinutesRemaining: number | null;  // null = not approaching limit
  weeklyMinutesRemaining: number | null;
}

/**
 * Parameters for the unified profile scoring function
 */
export interface ProfileScoreParams {
  sessionPercent: number;
  weeklyPercent: number;
  isRateLimited: boolean;
  rateLimitType?: 'session' | 'weekly';
  isAuthenticated: boolean;
  resetAt?: Date;
  // Velocity-based scoring (Phase 3)
  velocity?: VelocityData;
  estimatedTimeToLimit?: TimeToLimitData;
  // Capacity reservation (Phase 6)
  reservedCapacityPerHour?: number;
}

// ============================================
// Unified Scoring
// ============================================

/**
 * Unified profile score calculation.
 * Used both for UI display (availability ranking) and swap selection.
 *
 * Score breakdown:
 * - Base: 100
 * - Unauthenticated: -1000
 * - Rate limited (weekly): -500, (session): -200
 * - Time-to-reset bonus: up to +50 for profiles resetting sooner
 * - Weekly usage penalty: -0.5 per percent
 * - Session usage penalty: -0.2 per percent
 * - Remaining capacity bonus: +0.3 per percent of remaining weekly headroom
 * - Velocity penalty: -10 per %/min of session velocity (fast consumption = lower score)
 * - Time-to-limit penalty: -50 if <10min, -20 if 10-30min to predicted limit
 * - Reserved capacity penalty: treated as additional usage
 */
export function calculateProfileScore(params: ProfileScoreParams): number {
  let score = 100;

  // Authentication is critical
  if (!params.isAuthenticated) {
    score -= 1000;
  }

  // Rate limit penalties with time-to-reset bonus
  if (params.isRateLimited) {
    if (params.rateLimitType === 'weekly') {
      score -= 500;
    } else {
      score -= 200;
    }

    // Bonus for profiles that reset sooner
    if (params.resetAt) {
      const hoursUntilReset = (params.resetAt.getTime() - Date.now()) / (1000 * 60 * 60);
      score += Math.max(0, 50 - hoursUntilReset);
    }
  }

  // Factor in reserved capacity as effective additional usage
  let effectiveWeeklyPercent = params.weeklyPercent;
  let effectiveSessionPercent = params.sessionPercent;
  if (params.reservedCapacityPerHour && params.reservedCapacityPerHour > 0) {
    effectiveWeeklyPercent += params.reservedCapacityPerHour;
    effectiveSessionPercent += params.reservedCapacityPerHour;
  }

  // Usage penalties (prefer lower usage)
  score -= effectiveWeeklyPercent * 0.5;
  score -= effectiveSessionPercent * 0.2;

  // Remaining capacity bonus (more headroom = better)
  const remainingWeeklyCapacity = Math.max(0, 100 - effectiveWeeklyPercent);
  score += remainingWeeklyCapacity * 0.3;

  // Velocity-based penalties
  if (params.velocity && params.velocity.confidence !== 'low') {
    // Penalize profiles consuming fast (session velocity matters most for immediate switching)
    if (params.velocity.sessionVelocity > 0) {
      score -= params.velocity.sessionVelocity * 10;
    }
    if (params.velocity.weeklyVelocity > 0) {
      score -= params.velocity.weeklyVelocity * 5;
    }
  }

  // Time-to-limit penalties (predicted to hit limit soon)
  if (params.estimatedTimeToLimit) {
    const sessionMin = params.estimatedTimeToLimit.sessionMinutesRemaining;
    if (sessionMin !== null) {
      if (sessionMin < 10) {
        score -= 50;
      } else if (sessionMin < 30) {
        score -= 20;
      }
    }
    const weeklyMin = params.estimatedTimeToLimit.weeklyMinutesRemaining;
    if (weeklyMin !== null) {
      if (weeklyMin < 30) {
        score -= 50;
      } else if (weeklyMin < 60) {
        score -= 20;
      }
    }
  }

  return Math.round(score * 100) / 100;
}

// ============================================
// Availability Check
// ============================================

/**
 * Check if a profile is available for use based on all criteria
 */
function checkProfileAvailability(
  profile: ClaudeProfile,
  settings: ClaudeAutoSwitchSettings
): { available: boolean; reason?: string } {
  // Check authentication
  if (!isProfileAuthenticated(profile)) {
    return { available: false, reason: 'not authenticated' };
  }

  // Check explicit rate limit (from 429 errors)
  const rateLimitStatus = isProfileRateLimited(profile);
  if (rateLimitStatus.limited) {
    return {
      available: false,
      reason: `rate limited (${rateLimitStatus.type}, resets ${rateLimitStatus.resetAt?.toISOString() || 'unknown'})`
    };
  }

  // Check usage thresholds
  if (profile.usage) {
    // Weekly threshold check (more important - longer reset time)
    // Using >= to reject profiles AT or ABOVE threshold (e.g., 95% is rejected when threshold is 95%)
    // This is intentional: we want to switch proactively BEFORE hitting hard limits
    if (profile.usage.weeklyUsagePercent >= settings.weeklyThreshold) {
      return {
        available: false,
        reason: `weekly usage ${profile.usage.weeklyUsagePercent}% >= threshold ${settings.weeklyThreshold}%`
      };
    }

    // Session threshold check
    // Using >= to reject profiles AT or ABOVE threshold (same rationale as weekly)
    if (profile.usage.sessionUsagePercent >= settings.sessionThreshold) {
      return {
        available: false,
        reason: `session usage ${profile.usage.sessionUsagePercent}% >= threshold ${settings.sessionThreshold}%`
      };
    }
  }

  return { available: true };
}

// ============================================
// Fallback Score (extends unified score with overage penalties)
// ============================================

/**
 * Calculate a fallback score for when no profiles meet all criteria.
 * Builds on calculateProfileScore() and adds overage-based penalties.
 */
function calculateFallbackScore(
  profile: ClaudeProfile,
  settings: ClaudeAutoSwitchSettings,
  velocityData?: VelocityData,
  timeToLimit?: TimeToLimitData,
  reservedCapacity?: number
): number {
  const rateLimitStatus = isProfileRateLimited(profile);

  // Get base score from unified calculator
  let score = calculateProfileScore({
    sessionPercent: profile.usage?.sessionUsagePercent ?? 0,
    weeklyPercent: profile.usage?.weeklyUsagePercent ?? 0,
    isRateLimited: rateLimitStatus.limited,
    rateLimitType: rateLimitStatus.type,
    isAuthenticated: isProfileAuthenticated(profile),
    resetAt: rateLimitStatus.resetAt,
    velocity: velocityData,
    estimatedTimeToLimit: timeToLimit,
    reservedCapacityPerHour: reservedCapacity,
  });

  // Additional overage penalties for fallback selection
  if (profile.usage) {
    const weeklyOverage = Math.max(0, profile.usage.weeklyUsagePercent - settings.weeklyThreshold);
    const sessionOverage = Math.max(0, profile.usage.sessionUsagePercent - settings.sessionThreshold);
    score -= weeklyOverage * 2;
    score -= sessionOverage;
  }

  return score;
}

// ============================================
// Profile Selection
// ============================================

/**
 * Get the best profile to switch to based on priority order and availability
 *
 * Selection Logic:
 * 1. Filter to candidates (excluding the current profile and locked profiles)
 * 2. Check each profile's availability (auth, rate limit, thresholds)
 * 3. Sort by user's priority order
 * 4. Return the first available profile in priority order
 * 5. If none available, return the "least bad" option based on fallback scoring
 *
 * @param profiles - All Claude profiles
 * @param settings - Auto-switch settings (contains thresholds)
 * @param excludeProfileId - Profile ID to exclude (usually the current/failing one)
 * @param priorityOrder - User's configured priority order (array of unified IDs like 'oauth-{id}')
 * @param options - Additional options for velocity, lock, and capacity data
 */
export function getBestAvailableProfile(
  profiles: ClaudeProfile[],
  settings: ClaudeAutoSwitchSettings,
  excludeProfileId?: string,
  priorityOrder: string[] = [],
  options?: {
    lockedProfileIds?: Set<string>;
    getVelocity?: (profileId: string) => VelocityData | undefined;
    getTimeToLimit?: (profileId: string) => TimeToLimitData | undefined;
    getReservedCapacity?: (profileId: string) => number;
  }
): ClaudeProfile | null {
  const lockedIds = options?.lockedProfileIds ?? new Set<string>();

  // Get all profiles except the excluded one and locked ones
  const candidates = profiles.filter(p =>
    p.id !== excludeProfileId && !lockedIds.has(p.id)
  );

  if (candidates.length === 0) {
    return null;
  }

  if (isDebug) {
    console.warn('[ProfileScorer] Evaluating', candidates.length, 'candidate profiles (excluding:', excludeProfileId, ', locked:', Array.from(lockedIds), ')');
    console.warn('[ProfileScorer] Priority order:', priorityOrder);
    console.warn('[ProfileScorer] Thresholds: session =', settings.sessionThreshold, '%, weekly =', settings.weeklyThreshold, '%');
  }

  // Score and check availability for each profile
  const scoredProfiles: ScoredProfile[] = candidates.map(profile => {
    const unifiedId = `oauth-${profile.id}`;
    const priorityIndex = priorityOrder.indexOf(unifiedId);
    const availability = checkProfileAvailability(profile, settings);

    // Get velocity and capacity data if available
    const velocityData = options?.getVelocity?.(profile.id);
    const timeToLimit = options?.getTimeToLimit?.(profile.id);
    const reservedCapacity = options?.getReservedCapacity?.(profile.id);

    const fallbackScore = calculateFallbackScore(
      profile, settings, velocityData, timeToLimit, reservedCapacity
    );

    if (isDebug) {
      console.warn('[ProfileScorer] Scoring profile:', profile.name, '(', profile.id, ')');
      console.warn('[ProfileScorer]   Priority index:', priorityIndex === -1 ? 'not in list (Infinity)' : priorityIndex);
      console.warn('[ProfileScorer]   Available:', availability.available, availability.reason ? `(${availability.reason})` : '');
      console.warn('[ProfileScorer]   Usage:', profile.usage ? `session=${profile.usage.sessionUsagePercent}%, weekly=${profile.usage.weeklyUsagePercent}%` : 'unknown');
      console.warn('[ProfileScorer]   Fallback score:', fallbackScore);
      if (velocityData) {
        console.warn('[ProfileScorer]   Velocity:', `session=${velocityData.sessionVelocity.toFixed(2)}%/min, weekly=${velocityData.weeklyVelocity.toFixed(2)}%/min (${velocityData.confidence})`);
      }
      if (reservedCapacity) {
        console.warn('[ProfileScorer]   Reserved capacity:', reservedCapacity, '%/hour');
      }
    }

    return {
      profile,
      score: fallbackScore,
      priorityIndex: priorityIndex === -1 ? Infinity : priorityIndex,
      isAvailable: availability.available,
      unavailableReason: availability.reason
    };
  });

  // Sort by:
  // 1. Available profiles first
  // 2. Within available: by priority index (lower = higher priority)
  // 3. Within unavailable: by fallback score (higher = better)
  scoredProfiles.sort((a, b) => {
    // Available profiles always come first
    if (a.isAvailable !== b.isAvailable) {
      return a.isAvailable ? -1 : 1;
    }

    // For available profiles, sort by priority order
    if (a.isAvailable && b.isAvailable) {
      // If both have priority indices, use them
      if (a.priorityIndex !== b.priorityIndex) {
        return a.priorityIndex - b.priorityIndex;
      }
      // Tiebreaker: prefer higher score (lower usage, better velocity)
      return b.score - a.score;
    }

    // For unavailable profiles, sort by fallback score (for "least bad" selection)
    return b.score - a.score;
  });

  const best = scoredProfiles[0];

  if (best.isAvailable) {
    console.warn('[ProfileScorer] Best available profile:', best.profile.name, '(priority index:', best.priorityIndex, ', score:', best.score, ')');
    return best.profile;
  }

  // No profile meets all criteria - check if we should return the least bad option
  // Only return if it has a positive score (meaning it might still work)
  if (best.score > 0) {
    console.warn('[ProfileScorer] No ideal profile available, using least-bad option:', best.profile.name,
      '(score:', best.score, ', reason:', best.unavailableReason, ')');
    return best.profile;
  }

  // All profiles are truly unusable
  console.warn('[ProfileScorer] No usable profile available, all have issues');
  return null;
}

// ============================================
// Proactive Switch Decision
// ============================================

/**
 * Determine if we should proactively switch profiles based on current usage
 * and consumption velocity predictions.
 */
export function shouldProactivelySwitch(
  profile: ClaudeProfile,
  allProfiles: ClaudeProfile[],
  settings: ClaudeAutoSwitchSettings,
  priorityOrder: string[] = [],
  velocityData?: VelocityData,
  timeToLimit?: TimeToLimitData
): { shouldSwitch: boolean; reason?: string; suggestedProfile?: ClaudeProfile } {
  if (!settings.enabled) {
    return { shouldSwitch: false };
  }

  if (!profile?.usage) {
    return { shouldSwitch: false };
  }

  const usage = profile.usage;

  // Check threshold-based triggers (existing behavior)
  if (usage.weeklyUsagePercent >= settings.weeklyThreshold) {
    const bestProfile = getBestAvailableProfile(allProfiles, settings, profile.id, priorityOrder);
    if (bestProfile) {
      return {
        shouldSwitch: true,
        reason: `Weekly usage at ${usage.weeklyUsagePercent}% (threshold: ${settings.weeklyThreshold}%)`,
        suggestedProfile: bestProfile
      };
    }
  }

  if (usage.sessionUsagePercent >= settings.sessionThreshold) {
    const bestProfile = getBestAvailableProfile(allProfiles, settings, profile.id, priorityOrder);
    if (bestProfile) {
      return {
        shouldSwitch: true,
        reason: `Session usage at ${usage.sessionUsagePercent}% (threshold: ${settings.sessionThreshold}%)`,
        suggestedProfile: bestProfile
      };
    }
  }

  // Velocity-based early switch (only if confidence is medium or high)
  if (velocityData && velocityData.confidence !== 'low' && timeToLimit) {
    // If predicted to hit session threshold within 5 minutes, switch now
    if (timeToLimit.sessionMinutesRemaining !== null && timeToLimit.sessionMinutesRemaining < 5) {
      const bestProfile = getBestAvailableProfile(allProfiles, settings, profile.id, priorityOrder);
      if (bestProfile) {
        return {
          shouldSwitch: true,
          reason: `Predicted to hit session limit in ~${Math.round(timeToLimit.sessionMinutesRemaining)} min (velocity: ${velocityData.sessionVelocity.toFixed(1)}%/min)`,
          suggestedProfile: bestProfile
        };
      }
    }

    // If predicted to hit weekly threshold within 30 minutes, switch now
    if (timeToLimit.weeklyMinutesRemaining !== null && timeToLimit.weeklyMinutesRemaining < 30) {
      const bestProfile = getBestAvailableProfile(allProfiles, settings, profile.id, priorityOrder);
      if (bestProfile) {
        return {
          shouldSwitch: true,
          reason: `Predicted to hit weekly limit in ~${Math.round(timeToLimit.weeklyMinutesRemaining)} min (velocity: ${velocityData.weeklyVelocity.toFixed(1)}%/min)`,
          suggestedProfile: bestProfile
        };
      }
    }
  }

  return { shouldSwitch: false };
}

// ============================================
// Display Sorting
// ============================================

/**
 * Get profiles sorted by availability (best first)
 * This is a simpler sort that doesn't consider priority order - used for display purposes
 */
export function getProfilesSortedByAvailability(profiles: ClaudeProfile[]): ClaudeProfile[] {
  return [...profiles].sort((a, b) => {
    // Authenticated profiles first
    const aAuth = isProfileAuthenticated(a);
    const bAuth = isProfileAuthenticated(b);
    if (aAuth !== bAuth) {
      return aAuth ? -1 : 1;
    }

    // Not rate-limited profiles first
    const aLimited = isProfileRateLimited(a);
    const bLimited = isProfileRateLimited(b);

    if (aLimited.limited !== bLimited.limited) {
      return aLimited.limited ? 1 : -1;
    }

    // If both limited, sort by reset time
    if (aLimited.limited && bLimited.limited && aLimited.resetAt && bLimited.resetAt) {
      return aLimited.resetAt.getTime() - bLimited.resetAt.getTime();
    }

    // Sort by lower weekly usage
    const aWeekly = a.usage?.weeklyUsagePercent ?? 0;
    const bWeekly = b.usage?.weeklyUsagePercent ?? 0;
    if (aWeekly !== bWeekly) {
      return aWeekly - bWeekly;
    }

    // Sort by lower session usage
    const aSession = a.usage?.sessionUsagePercent ?? 0;
    const bSession = b.usage?.sessionUsagePercent ?? 0;
    return aSession - bSession;
  });
}
