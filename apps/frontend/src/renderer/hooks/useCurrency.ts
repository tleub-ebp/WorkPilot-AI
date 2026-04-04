import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

/**
 * Currency conversion hook.
 *
 * - Fetches USD→EUR rate from frankfurter.app (free, no key required)
 * - Caches rate for 1 hour to avoid excessive requests
 * - Falls back to a sensible default if the API is unreachable
 * - Returns a formatter that converts USD amounts to local currency
 */

interface CurrencyCache {
	rate: number;
	fetchedAt: number;
}

const CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour
const FALLBACK_EUR_RATE = 0.92;

let sharedCache: CurrencyCache | null = null;
let fetchPromise: Promise<number> | null = null;

async function fetchEurRate(): Promise<number> {
	// Reuse in-flight request
	if (fetchPromise !== null) return fetchPromise;

	// Return cached value if fresh
	if (sharedCache && Date.now() - sharedCache.fetchedAt < CACHE_TTL_MS) {
		return sharedCache.rate;
	}

	fetchPromise = (async () => {
		try {
			const res = await fetch(
				"https://api.frankfurter.dev/v1/latest?from=USD&to=EUR",
			);
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const data = await res.json();
			const rate = data?.rates?.EUR;
			if (typeof rate !== "number") throw new Error("Invalid response");
			sharedCache = { rate, fetchedAt: Date.now() };
			return rate;
		} catch {
			// Return cached value even if stale, or fallback
			return sharedCache?.rate ?? FALLBACK_EUR_RATE;
		} finally {
			fetchPromise = null;
		}
	})();

	return fetchPromise;
}

/**
 * Maps i18n language codes to their native currency.
 * USD is the internal reference currency; conversion only happens for non-USD locales.
 */
function getCurrencyForLocale(lang: string): {
	code: string;
	symbol: string;
	needsConversion: boolean;
} {
	if (lang === "fr") {
		return { code: "EUR", symbol: "\u20AC", needsConversion: true };
	}
	return { code: "USD", symbol: "$", needsConversion: false };
}

export function useCurrency() {
	const { i18n } = useTranslation();
	const lang = i18n.language;
	const currency = getCurrencyForLocale(lang);

	const [rate, setRate] = useState<number>(
		sharedCache?.rate ?? (currency.needsConversion ? FALLBACK_EUR_RATE : 1),
	);
	const mountedRef = useRef(true);

	useEffect(() => {
		mountedRef.current = true;
		if (currency.needsConversion) {
			fetchEurRate().then((r) => {
				if (mountedRef.current) setRate(r);
			});
		} else {
			setRate(1);
		}
		return () => {
			mountedRef.current = false;
		};
	}, [currency.needsConversion]);

	/** Convert a USD amount to the user's local currency. */
	const convert = useCallback(
		(usdAmount: number): number => {
			if (!currency.needsConversion) return usdAmount;
			return Math.round(usdAmount * rate * 100) / 100;
		},
		[rate, currency.needsConversion],
	);

	/** Format a USD amount as a localized currency string (e.g. "$5" or "5 €"). */
	const format = useCallback(
		(usdAmount: number): string => {
			const localAmount = convert(usdAmount);
			if (currency.code === "EUR") {
				return `${localAmount}\u00A0\u20AC`;
			}
			return `$${localAmount}`;
		},
		[convert, currency.code],
	);

	/** Convert a local-currency amount back to USD for storage. */
	const toUsd = useCallback(
		(localAmount: number): number => {
			if (!currency.needsConversion || rate === 0) return localAmount;
			return Math.round((localAmount / rate) * 100) / 100;
		},
		[rate, currency.needsConversion],
	);

	return {
		/** ISO currency code (USD, EUR) */
		currencyCode: currency.code,
		/** Currency symbol ($, €) */
		symbol: currency.symbol,
		/** Current USD→local rate */
		rate,
		/** Convert USD → local */
		convert,
		/** Format USD amount to display string */
		format,
		/** Convert local → USD */
		toUsd,
	};
}
