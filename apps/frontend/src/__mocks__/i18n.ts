/**
 * Mock for i18n module to prevent SSR transformation issues in tests
 */

export const defaultNS = "common";

export const resources = {
	en: {},
	fr: {},
};

const mockI18n = {
	use: (() => mockI18n) as any,
	init: (() => {}) as any,
	t: ((key: string) => key) as any,
	changeLanguage: (() => {}) as any,
	language: "en",
};

export default mockI18n;
