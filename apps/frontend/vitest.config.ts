import { resolve } from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
	test: {
		globals: true,
		environment: "jsdom",
		include: [
			"src/**/*.test.ts",
			"src/**/*.test.tsx",
			"src/**/*.spec.ts",
			"src/**/*.spec.tsx",
		],
		exclude: ["node_modules", "dist", "out"],
		coverage: {
			provider: "v8",
			reporter: ["text", "json", "html"],
			include: ["src/**/*.ts", "src/**/*.tsx"],
			exclude: [
				"src/**/*.test.ts",
				"src/**/*.test.tsx",
				"src/**/*.spec.ts",
				"src/**/*.spec.tsx",
				"src/**/*.d.ts",
			],
		},
		// Mock Electron modules for unit tests
		alias: {
			electron: resolve(__dirname, "src/__mocks__/electron.ts"),
			// electron-log requires the electron binary at module load time via CJS require('electron').
			// In CI, electron is installed with --ignore-scripts so the binary is absent and index.js throws.
			// Aliasing at the vitest level prevents any test from ever loading the real electron-log.
			"electron-log/main.js": resolve(
				__dirname,
				"src/__mocks__/electron-log-main.ts",
			),
			"@sentry/electron/main": resolve(
				__dirname,
				"src/__mocks__/sentry-electron-main.ts",
			),
			"@sentry/electron/renderer": resolve(
				__dirname,
				"src/__mocks__/sentry-electron-renderer.ts",
			),
			// Mock i18n to prevent SSR transformation issues
			"@shared/i18n": resolve(__dirname, "src/__mocks__/i18n.ts"),
		},
		// Setup files for test environment - use setupFiles to avoid vitest import issues
		setupFiles: ["./src/__tests__/testSetup.ts"],
		// Suppress internal worker state errors from vitest 2.x
		dangerouslyIgnoreUnhandledErrors: true,
		// Prevent vitest import issues
		testTimeout: 30000,
		hookTimeout: 30000,
	},
	resolve: {
		alias: {
			"@": resolve(__dirname, "src/renderer"),
			"@main": resolve(__dirname, "src/main"),
			"@renderer": resolve(__dirname, "src/renderer"),
			"@shared": resolve(__dirname, "src/shared"),
			"@preload": resolve(__dirname, "src/preload"),
			"@features": resolve(__dirname, "src/renderer/features"),
			"@components": resolve(__dirname, "src/renderer/shared/components"),
			"@hooks": resolve(__dirname, "src/renderer/shared/hooks"),
			"@lib": resolve(__dirname, "src/renderer/lib"),
		},
	},
});
