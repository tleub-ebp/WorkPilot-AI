/**
 * Fetches the live model catalog for a given AI provider from the backend.
 *
 * Backed by `GET /providers/models/{provider}/catalog`, which is itself
 * backed by a 6-hour disk cache and falls back to a static catalog when
 * the provider's API is unreachable or no API key is configured.
 *
 * The hook returns the most current data it can offer at every moment:
 *  - while the network call is in flight, it serves the static catalog
 *    from `getModelsForProvider()` so the UI never sees an empty dropdown
 *  - once the response arrives, it switches to the live (or cached) list
 *  - `refresh()` forces a bypass of the backend cache
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
	AVAILABLE_MODELS,
	getModelsForProvider,
} from "../../shared/constants";

export type CatalogSource = "live" | "cache" | "static";

/** Subset of ProviderModel — `tier` and `supportsThinking` are optional here
 * because the legacy AVAILABLE_MODELS catalog used as instant fallback for
 * Claude does not expose them. */
export interface CatalogModel {
	value: string;
	label: string;
	tier?: "flagship" | "standard" | "fast" | "local";
	supportsThinking?: boolean;
}

export interface ProviderModelCatalog {
	models: readonly CatalogModel[];
	source: CatalogSource;
	fetchedAt: number | null;
	error: string | null;
	loading: boolean;
	refresh: () => void;
}

interface CatalogResponse {
	provider: string;
	models: CatalogModel[];
	source: CatalogSource;
	fetchedAt: number | null;
	error: string | null;
}

/** Static catalog used until the backend response arrives. */
function staticCatalog(provider: string): readonly CatalogModel[] {
	const isClaude =
		!provider || provider === "anthropic" || provider === "claude";
	return isClaude ? AVAILABLE_MODELS : getModelsForProvider(provider);
}

export function useProviderModelCatalog(
	provider: string,
): ProviderModelCatalog {
	const [models, setModels] = useState<readonly CatalogModel[]>(() =>
		staticCatalog(provider),
	);
	const [source, setSource] = useState<CatalogSource>("static");
	const [fetchedAt, setFetchedAt] = useState<number | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [loading, setLoading] = useState(false);
	const [bumpToken, setBumpToken] = useState(0);
	const lastProviderRef = useRef<string>("");

	const refresh = useCallback(() => setBumpToken((n) => n + 1), []);

	useEffect(() => {
		// Reset to static catalog whenever the provider changes; this keeps
		// dropdowns coherent with the new provider while the live fetch runs.
		if (lastProviderRef.current !== provider) {
			lastProviderRef.current = provider;
			setModels(staticCatalog(provider));
			setSource("static");
			setFetchedAt(null);
			setError(null);
		}

		if (!provider) return;

		const controller = new AbortController();
		const backendUrl = import.meta.env?.VITE_BACKEND_URL || "";
		const url = `${backendUrl}/providers/models/${encodeURIComponent(
			provider,
		)}/catalog${bumpToken > 0 ? "?refresh=true" : ""}`;

		setLoading(true);
		fetch(url, { signal: controller.signal })
			.then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				const contentType = res.headers.get("content-type") || "";
				if (!contentType.includes("application/json")) {
					throw new Error("non-json");
				}
				return res.json() as Promise<CatalogResponse>;
			})
			.then((data) => {
				if (Array.isArray(data?.models) && data.models.length > 0) {
					setModels(data.models);
					setSource(data.source);
					setFetchedAt(data.fetchedAt);
					setError(data.error);
				} else {
					// Empty live catalog (e.g. no key) — keep static fallback,
					// but surface the source/error so the UI can show a hint.
					setSource(data?.source ?? "static");
					setFetchedAt(data?.fetchedAt ?? null);
					setError(data?.error ?? null);
				}
			})
			.catch((err) => {
				if (err?.name === "AbortError") return;
				setError(err?.message ?? "fetch_failed");
			})
			.finally(() => setLoading(false));

		return () => controller.abort();
	}, [provider, bumpToken]);

	return { models, source, fetchedAt, error, loading, refresh };
}
