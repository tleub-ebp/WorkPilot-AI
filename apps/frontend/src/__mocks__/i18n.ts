/**
 * Mock for i18n module to prevent SSR transformation issues in tests
 */

export const defaultNS = "common";

export const resources = {
	en: {},
	fr: {},
};

const mockI18n = {
	// biome-ignore lint/suspicious/noExplicitAny: Mock file - type flexibility needed for testing
	use: (() => mockI18n) as any,
	// biome-ignore lint/suspicious/noExplicitAny: Mock file - type flexibility needed for testing
	// biome-ignore lint/suspicious/noEmptyBlockStatements: Mock file - empty function is intentional
	init: (() => {}) as any,
	// biome-ignore lint/suspicious/noExplicitAny: Mock file - type flexibility needed for testing
	t: ((key: string) => key) as any,
	// biome-ignore lint/suspicious/noExplicitAny: Mock file - type flexibility needed for testing
	// biome-ignore lint/suspicious/noEmptyBlockStatements: Mock file - empty function is intentional
	changeLanguage: (() => {}) as any,
	language: "en",
};

export default mockI18n;
