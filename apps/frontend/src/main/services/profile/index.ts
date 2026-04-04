/**
 * Profile Service - Barrel Export
 *
 * Re-exports all profile-related functionality for convenient importing.
 * Main process code should import from this index file.
 */

// Re-export types from shared for convenience
export type {
	APIProfile,
	DiscoverModelsError,
	DiscoverModelsResult,
	ModelInfo,
	ProfileFormData,
	ProfilesFile,
	TestConnectionResult,
} from "@shared/types/profile";
// Profile Manager utilities
export {
	atomicModifyProfiles,
	generateProfileId,
	getProfilesFilePath,
	loadProfilesFile,
	saveProfilesFile,
	validateFilePermissions,
	withProfilesLock,
} from "./profile-manager";

export type { CreateProfileInput, UpdateProfileInput } from "./profile-service";
// Profile Service
export {
	createProfile,
	deleteProfile,
	discoverModels,
	getAPIProfileEnv,
	testConnection,
	updateProfile,
	validateApiKey,
	validateBaseUrl,
	validateProfileNameUnique,
} from "./profile-service";
