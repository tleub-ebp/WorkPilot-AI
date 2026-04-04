/**
 * @vitest-environment jsdom
 */

/**
 * Integration tests for Frontend ↔ Backend Provider API
 * Tests the complete flow: provider selection, API key testing, generation
 * with mocked backend responses.
 * Improvement 6.2: Integration tests Frontend ↔ Backend (provider API)
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock electronAPI for provider-related IPC calls
const mockGetSettings = vi.fn();
const mockSaveSettings = vi.fn();
const mockGetAPIProfiles = vi.fn();
const mockSaveAPIProfile = vi.fn();
const mockUpdateAPIProfile = vi.fn();
const mockDeleteAPIProfile = vi.fn();
const mockSetActiveAPIProfile = vi.fn();
const mockTestConnection = vi.fn();
const mockDiscoverModels = vi.fn();
const mockGetClaudeCodeOnboardingStatus = vi.fn();

vi.stubGlobal("globalThis", {
	electronAPI: {
		getSettings: mockGetSettings,
		saveSettings: mockSaveSettings,
		getAPIProfiles: mockGetAPIProfiles,
		saveAPIProfile: mockSaveAPIProfile,
		updateAPIProfile: mockUpdateAPIProfile,
		deleteAPIProfile: mockDeleteAPIProfile,
		setActiveAPIProfile: mockSetActiveAPIProfile,
		testConnection: mockTestConnection,
		discoverModels: mockDiscoverModels,
		getClaudeCodeOnboardingStatus: mockGetClaudeCodeOnboardingStatus,
	},
});

// Mock toast
vi.mock("../../../renderer/hooks/use-toast", () => ({
	toast: vi.fn(),
}));

// Mock Sentry
vi.mock("../../../renderer/lib/sentry", () => ({
	markSettingsLoaded: vi.fn(),
}));

describe("Frontend ↔ Backend Provider API Integration", () => {
	let useSettingsStore: typeof import("../../renderer/stores/settings-store").useSettingsStore;
	let loadSettings: typeof import("../../renderer/stores/settings-store").loadSettings;
	let loadProfiles: typeof import("../../renderer/stores/settings-store").loadProfiles;

	beforeEach(async () => {
		vi.clearAllMocks();
		vi.resetModules();

		const storeModule = await import("../../renderer/stores/settings-store");
		useSettingsStore = storeModule.useSettingsStore;
		loadSettings = storeModule.loadSettings;
		loadProfiles = storeModule.loadProfiles;
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe("Scenario: Provider selection flow", () => {
		it("should load profiles and identify available providers", async () => {
			const profiles = [
				{
					id: "profile-openai",
					name: "My OpenAI",
					baseUrl: "https://api.openai.com/v1",
					apiKey: "sk-test-openai-key",
					createdAt: Date.now(),
					updatedAt: Date.now(),
				},
				{
					id: "profile-anthropic",
					name: "My Anthropic",
					baseUrl: "https://api.anthropic.com",
					apiKey: "sk-ant-test-key",
					createdAt: Date.now(),
					updatedAt: Date.now(),
				},
			];

			mockGetAPIProfiles.mockResolvedValue({
				success: true,
				data: { profiles, activeProfileId: "profile-anthropic" },
			});

			await loadProfiles();

			const state = useSettingsStore.getState();
			expect(state.profiles).toHaveLength(2);
			expect(state.activeProfileId).toBe("profile-anthropic");
			expect(state.profiles.find((p) => p.name === "My OpenAI")).toBeDefined();
		});

		it("should switch active profile", async () => {
			useSettingsStore.setState({
				profiles: [
					{
						id: "p1",
						name: "Profile 1",
						baseUrl: "https://api.openai.com",
						apiKey: "key1",
						createdAt: Date.now(),
						updatedAt: Date.now(),
					},
					{
						id: "p2",
						name: "Profile 2",
						baseUrl: "https://api.anthropic.com",
						apiKey: "key2",
						createdAt: Date.now(),
						updatedAt: Date.now(),
					},
				],
				activeProfileId: "p1",
			});

			mockSetActiveAPIProfile.mockResolvedValue({ success: true });

			const result = await useSettingsStore.getState().setActiveProfile("p2");

			expect(result).toBe(true);
			expect(useSettingsStore.getState().activeProfileId).toBe("p2");
			expect(mockSetActiveAPIProfile).toHaveBeenCalledWith("p2");
		});
	});

	describe("Scenario: API key testing flow", () => {
		it("should test valid API key successfully", async () => {
			mockTestConnection.mockResolvedValue({
				success: true,
				data: {
					success: true,
					message: "Connection successful. API key is valid.",
				},
			});

			const result = await useSettingsStore
				.getState()
				.testConnection("https://api.openai.com/v1", "sk-valid-key");

			expect(result).toBeDefined();
			expect(result?.success).toBe(true);
			expect(result?.message).toContain("successful");
			expect(useSettingsStore.getState().isTestingConnection).toBe(false);
		});

		it("should handle invalid API key", async () => {
			mockTestConnection.mockResolvedValue({
				success: true,
				data: {
					success: false,
					errorType: "auth",
					message: "Invalid API key. Please check your credentials.",
				},
			});

			const result = await useSettingsStore
				.getState()
				.testConnection("https://api.openai.com/v1", "sk-invalid-key");

			expect(result).toBeDefined();
			expect(result?.success).toBe(false);
			expect(result?.errorType).toBe("auth");
		});

		it("should handle network errors during testing", async () => {
			mockTestConnection.mockResolvedValue({
				success: true,
				data: {
					success: false,
					errorType: "network",
					message: "Could not reach the API endpoint.",
				},
			});

			const result = await useSettingsStore
				.getState()
				.testConnection("https://api.unreachable.com/v1", "sk-key");

			expect(result).toBeDefined();
			expect(result?.success).toBe(false);
			expect(result?.errorType).toBe("network");
		});

		it("should handle timeout during testing", async () => {
			mockTestConnection.mockResolvedValue({
				success: true,
				data: {
					success: false,
					errorType: "timeout",
					message: "Connection timed out after 10s.",
				},
			});

			const result = await useSettingsStore
				.getState()
				.testConnection("https://api.slow-server.com/v1", "sk-key");

			expect(result?.errorType).toBe("timeout");
		});
	});

	describe("Scenario: Model discovery flow", () => {
		it("should discover models from a valid endpoint", async () => {
			mockDiscoverModels.mockResolvedValue({
				success: true,
				data: {
					models: [
						{ id: "gpt-4", display_name: "GPT-4" },
						{ id: "gpt-3.5-turbo", display_name: "GPT-3.5 Turbo" },
					],
				},
			});

			const models = await useSettingsStore
				.getState()
				.discoverModels("https://api.openai.com/v1", "sk-valid-key");

			expect(models).toBeDefined();
			expect(models).toHaveLength(2);
			expect(models?.[0].id).toBe("gpt-4");
		});

		it("should cache models and reuse for same endpoint", async () => {
			mockDiscoverModels.mockResolvedValue({
				success: true,
				data: {
					models: [{ id: "model-1", display_name: "Model 1" }],
				},
			});

			// First call - should hit IPC
			await useSettingsStore
				.getState()
				.discoverModels("https://api.test.com", "sk-test-key1");
			// Second call with same key - should use cache
			const models = await useSettingsStore
				.getState()
				.discoverModels("https://api.test.com", "sk-test-key1");

			expect(mockDiscoverModels).toHaveBeenCalledTimes(1);
			expect(models).toHaveLength(1);
		});

		it("should handle unsupported endpoint", async () => {
			mockDiscoverModels.mockResolvedValue({
				success: false,
				error: "Endpoint does not support model discovery",
			});

			const models = await useSettingsStore
				.getState()
				.discoverModels("https://api.no-models.com", "sk-key");

			expect(models).toBeNull();
			expect(useSettingsStore.getState().modelsError).toContain("not support");
		});
	});

	describe("Scenario: Full profile lifecycle", () => {
		it("should create → test → activate → use → delete a profile", async () => {
			const newProfile = {
				id: "new-profile",
				name: "Test Profile",
				baseUrl: "https://api.openai.com/v1",
				apiKey: "sk-test-lifecycle",
				createdAt: Date.now(),
				updatedAt: Date.now(),
			};

			// Step 1: Create profile
			mockSaveAPIProfile.mockResolvedValue({ success: true, data: newProfile });
			mockGetAPIProfiles.mockResolvedValue({
				success: true,
				data: { profiles: [newProfile], activeProfileId: "new-profile" },
			});

			const created = await useSettingsStore.getState().saveProfile({
				name: "Test Profile",
				baseUrl: "https://api.openai.com/v1",
				apiKey: "sk-test-lifecycle",
			} as { name: string; baseUrl: string; apiKey: string });
			expect(created).toBe(true);
			expect(useSettingsStore.getState().profiles).toHaveLength(1);

			// Step 2: Test connection
			mockTestConnection.mockResolvedValue({
				success: true,
				data: { success: true, message: "OK" },
			});

			const testResult = await useSettingsStore
				.getState()
				.testConnection("https://api.openai.com/v1", "sk-test-lifecycle");
			expect(testResult?.success).toBe(true);

			// Step 3: Activate profile
			mockSetActiveAPIProfile.mockResolvedValue({ success: true });
			await useSettingsStore.getState().setActiveProfile("new-profile");
			expect(useSettingsStore.getState().activeProfileId).toBe("new-profile");

			// Step 4: Delete profile
			mockDeleteAPIProfile.mockResolvedValue({ success: true });
			const deleted = await useSettingsStore
				.getState()
				.deleteProfile("new-profile");
			expect(deleted).toBe(true);
			expect(useSettingsStore.getState().profiles).toHaveLength(0);
			expect(useSettingsStore.getState().activeProfileId).toBeNull();
		});
	});

	describe("Scenario: Settings + profiles loading on app init", () => {
		it("should load settings and profiles in sequence", async () => {
			mockGetSettings.mockResolvedValue({
				success: true,
				data: { onboardingCompleted: true, autoBuildPath: "/test" },
			});

			mockGetAPIProfiles.mockResolvedValue({
				success: true,
				data: {
					profiles: [
						{
							id: "p1",
							name: "Profile",
							baseUrl: "https://api.test.com",
							apiKey: "key",
							createdAt: Date.now(),
							updatedAt: Date.now(),
						},
					],
					activeProfileId: "p1",
				},
			});

			// Simulate app initialization
			await loadSettings();
			await loadProfiles();

			const state = useSettingsStore.getState();
			expect(state.isLoading).toBe(false);
			expect(state.settings.onboardingCompleted).toBe(true);
			expect(state.profiles).toHaveLength(1);
			expect(state.activeProfileId).toBe("p1");
		});

		it("should handle partial failures gracefully", async () => {
			// Settings succeed but profiles fail
			mockGetSettings.mockResolvedValue({
				success: true,
				data: { onboardingCompleted: true },
			});
			mockGetAPIProfiles.mockRejectedValue(
				new Error("IPC channel not available"),
			);

			await loadSettings();
			await loadProfiles();

			const state = useSettingsStore.getState();
			expect(state.isLoading).toBe(false);
			expect(state.profilesError).toBe("IPC channel not available");
			// Settings should still be loaded
			expect(state.settings.onboardingCompleted).toBe(true);
		});
	});
});
