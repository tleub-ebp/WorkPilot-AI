/**
 * Mock for i18n module to prevent SSR transformation issues in tests
 */

import { vi } from "vitest";

export const defaultNS = "common";

export const resources = {
	en: {},
	fr: {},
};

const mockI18n = {
	use: vi.fn(() => mockI18n),
	init: vi.fn(),
	t: vi.fn((key: string) => key),
	changeLanguage: vi.fn(),
	language: "en",
};

export default mockI18n;
