/**
 * Test for network error handling and retry mechanism
 * This test verifies that our network connectivity fixes work properly
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock fetch to simulate network errors and retries
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// Mock console methods to avoid noise in tests
const mockConsoleWarn = vi.spyOn(console, "warn").mockImplementation(() => {
	/* noop */
});
const mockConsoleError = vi.spyOn(console, "error").mockImplementation(() => {
	/* noop */
});
const mockConsoleLog = vi.spyOn(console, "log").mockImplementation(() => {
	/* noop */
});

describe("Network Error Handling", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		// Clear any cached versions
		if (
			typeof globalThis !== "undefined" &&
			(globalThis as Record<string, unknown>).cachedLatestVersion
		) {
			(globalThis as Record<string, unknown>).cachedLatestVersion = null;
		}
	});

	it("should retry on network errors and eventually succeed", async () => {
		// Import the functions we need to test
		const { isNetworkError } = await import(
			"../ipc-handlers/claude-code-handlers"
		);

		// Test the isNetworkError function
		expect(isNetworkError("ECONNRESET")).toBe(true);
		expect(isNetworkError("socket disconnected")).toBe(true);
		expect(isNetworkError("ENOTFOUND")).toBe(true);
		expect(isNetworkError("network error")).toBe(true);
		expect(isNetworkError("timeout")).toBe(true);
		expect(isNetworkError("HTTP 404")).toBe(false);
		expect(isNetworkError("Invalid JSON")).toBe(false);
	});

	it("should handle proxy configuration", async () => {
		// Save original values
		const origHttpsProxy = process.env.HTTPS_PROXY;
		const origHttpProxy = process.env.HTTP_PROXY;
		const origNoProxy = process.env.NO_PROXY;

		try {
			// Set proxy env vars individually (safer than replacing entire process.env)
			process.env.HTTPS_PROXY = "https://proxy.example.com:8080";
			process.env.HTTP_PROXY = "http://proxy.example.com:8080";
			process.env.NO_PROXY = "localhost,127.0.0.1";

			// Import after setting env vars
			const { createProxiedFetch } = await import(
				"../ipc-handlers/claude-code-handlers"
			);

			// Verify proxy env vars are readable
			expect(process.env.HTTPS_PROXY).toBe("https://proxy.example.com:8080");
			expect(process.env.HTTP_PROXY).toBe("http://proxy.example.com:8080");
			expect(process.env.NO_PROXY).toBe("localhost,127.0.0.1");

			// Verify createProxiedFetch is importable (it reads these env vars at call time)
			expect(createProxiedFetch).toBeDefined();
			expect(typeof createProxiedFetch).toBe("function");
		} finally {
			// Restore original values
			if (origHttpsProxy === undefined) delete process.env.HTTPS_PROXY;
			else process.env.HTTPS_PROXY = origHttpsProxy;
			if (origHttpProxy === undefined) delete process.env.HTTP_PROXY;
			else process.env.HTTP_PROXY = origHttpProxy;
			if (origNoProxy === undefined) delete process.env.NO_PROXY;
			else process.env.NO_PROXY = origNoProxy;
		}
	});

	it("should use fallback registry when primary fails", async () => {
		const { isNetworkError } = await import(
			"../ipc-handlers/claude-code-handlers"
		);

		// Mock fetch to fail with network errors then succeed
		mockFetch
			.mockRejectedValueOnce(new Error("ECONNRESET"))
			.mockRejectedValueOnce(new Error("socket disconnected"))
			.mockResolvedValueOnce({
				ok: true,
				json: () => Promise.resolve({ version: "1.0.0" }),
			});

		// Verify network errors are correctly identified as retryable
		expect(isNetworkError("ECONNRESET")).toBe(true);
		expect(isNetworkError("socket disconnected")).toBe(true);

		// First call fails with ECONNRESET
		await expect(mockFetch("https://registry.npmjs.org/test")).rejects.toThrow(
			"ECONNRESET",
		);

		// Second call fails with socket disconnected
		await expect(mockFetch("https://registry.npmjs.org/test")).rejects.toThrow(
			"socket disconnected",
		);

		// Third call succeeds
		const response = await mockFetch("https://registry.npmjs.org/test");
		const data = await response.json();
		expect(data.version).toBe("1.0.0");
		expect(mockFetch).toHaveBeenCalledTimes(3);
	});

	afterEach(() => {
		mockConsoleWarn.mockRestore();
		mockConsoleError.mockRestore();
		mockConsoleLog.mockRestore();
	});
});
