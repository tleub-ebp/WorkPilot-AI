/**
 * Currency formatting utilities — live EUR/USD rate with 24h cache.
 */

// Module-level EUR rate cache (shared across all consumers)
let _eurRate = 0.92;
let _eurRateFetchedAt = 0;

/**
 * Fetch the current EUR/USD exchange rate from open.er-api.com.
 * Results are cached for 24 hours; on network failure the last known rate is kept.
 */
export async function getEurRate(): Promise<number> {
  const STALE_MS = 24 * 60 * 60 * 1000; // 24 h
  if (Date.now() - _eurRateFetchedAt < STALE_MS) return _eurRate;
  try {
    const res = await fetch('https://open.er-api.com/v6/latest/USD');
    if (res.ok) {
      const data = (await res.json()) as { rates?: Record<string, number> };
      const rate = data.rates?.EUR;
      if (typeof rate === 'number' && rate > 0) {
        _eurRate = rate;
        _eurRateFetchedAt = Date.now();
      }
    }
  } catch {
    // Keep existing cached rate on network error
  }
  return _eurRate;
}

/**
 * Format a USD cost for display, converting to EUR when the UI language is French.
 */
export function formatCurrency(
  usd: number,
  language: string,
  eurRate: number,
  decimals = 4,
): string {
  if (language.startsWith('fr')) {
    return `${(usd * eurRate).toFixed(decimals)}\u00A0\u20AC`;
  }
  return `$${usd.toFixed(decimals)}`;
}
