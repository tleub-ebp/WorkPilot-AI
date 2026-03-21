/**
 * Usage Formatting Utilities
 *
 * Shared utilities for formatting usage values and numbers.
 */

/**
 * Helper function to format large numbers with locale-aware compact notation
 */
export function formatUsageValue(value?: number | null, locale?: string): string | undefined {
  if (value == null) return undefined;

  if (typeof Intl !== 'undefined' && Intl.NumberFormat) {
    try {
      return new Intl.NumberFormat(locale, {
        notation: 'compact',
        compactDisplay: 'short',
        maximumFractionDigits: 2
      }).format(value);
    } catch {
      // Intl may fail in some environments, fall back to toString()
    }
  }
  return value.toString();
}
