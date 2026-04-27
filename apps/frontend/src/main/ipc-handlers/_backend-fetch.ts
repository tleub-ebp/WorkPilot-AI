/**
 * Shared helper for IPC handlers that proxy a request to the FastAPI
 * backend exposed by `apps/backend/provider_api.py`.
 *
 * Most handlers for the new "Phase 3-5" feature modules look the same:
 * read a JSON body from the renderer, POST/GET it to a backend endpoint,
 * forward the JSON response back. This module hides the boilerplate.
 */

const DEFAULT_BACKEND_URL = "http://127.0.0.1:8765";

export function getBackendUrl(): string {
	return (
		process.env.VITE_BACKEND_URL ||
		process.env.BACKEND_URL ||
		DEFAULT_BACKEND_URL
	);
}

export interface BackendError {
	success: false;
	error: string;
}

export type BackendResult<T> = ({ success: true } & T) | BackendError;

/**
 * Fetch a backend endpoint and return its JSON body.
 *
 * Errors are normalised to `{ success: false, error: "..." }` so renderer
 * stores can rely on a single shape. We never throw across the IPC boundary
 * (Electron will mangle the stack trace anyway).
 */
export async function backendFetch<T = Record<string, unknown>>(
	path: string,
	init?: RequestInit,
	timeoutMs = 30_000,
): Promise<BackendResult<T>> {
	const url = `${getBackendUrl()}${path}`;
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), timeoutMs);
	try {
		const res = await fetch(url, {
			headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
			signal: controller.signal,
			...init,
		});
		const text = await res.text();
		if (!res.ok) {
			return { success: false, error: text || `HTTP ${res.status}` };
		}
		try {
			return JSON.parse(text) as BackendResult<T>;
		} catch {
			return { success: false, error: "Backend returned non-JSON response" };
		}
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err);
		return { success: false, error: msg };
	} finally {
		clearTimeout(timer);
	}
}
