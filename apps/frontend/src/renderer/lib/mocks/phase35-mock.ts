/**
 * Browser-mode stubs for the 12 Phase 3-5 feature methods.
 *
 * They all return a `success: false` result with a clear message — the
 * features are backend-driven and don't make sense without an Electron
 * shell, but we keep the type contract so the renderer compiles.
 */

import type { Phase35FeaturesAPI } from "../../../preload/api/modules/phase35-features-api";

const browserUnavailable = (feature: string) =>
	Promise.resolve({
		success: false as const,
		error: `${feature} is only available in the Electron app (not in the browser dev preview).`,
	});

export const phase35Mock: Phase35FeaturesAPI = {
	scoreLongevity: () => browserUnavailable("Longevity scoring"),

	recordAgentRun: () => browserUnavailable("Agent health"),
	recordAgentRunBatch: () => browserUnavailable("Agent health"),
	scoreAgentHealth: () => browserUnavailable("Agent health"),
	scoreAllAgentHealth: () => browserUnavailable("Agent health"),
	resetAgentHealth: () => browserUnavailable("Agent health"),

	routeModel: () => browserUnavailable("Model routing"),
	compareModels: () => browserUnavailable("Model routing"),

	listDomains: () => browserUnavailable("Domain agents"),
	getDomainProfile: () => browserUnavailable("Domain agents"),
	buildDomainBundle: () => browserUnavailable("Domain agents"),

	scanCicdLog: () => browserUnavailable("CI/CD anomaly detection"),
	analyseCicdLogs: () => browserUnavailable("CI/CD anomaly detection"),

	scanLicenses: () => browserUnavailable("License governance"),
	classifyLicense: () => browserUnavailable("License governance"),

	scanArchitecture: () => browserUnavailable("Architecture drift"),
	saveArchBaseline: () => browserUnavailable("Architecture drift"),
	compareArchDrift: () => browserUnavailable("Architecture drift"),

	listGenerations: () => browserUnavailable("Generational testing"),
	captureGeneration: () => browserUnavailable("Generational testing"),
	compareGeneration: () => browserUnavailable("Generational testing"),
	deleteGeneration: () => browserUnavailable("Generational testing"),

	diffI18n: () => browserUnavailable("i18n auto-scaling"),
	skeletonI18n: () => browserUnavailable("i18n auto-scaling"),
	reportI18nFromDir: () => browserUnavailable("i18n auto-scaling"),

	optimizeContext: () => browserUnavailable("Cognitive context"),

	auditAppend: () => browserUnavailable("Audit trail"),
	auditAppendDecision: () => browserUnavailable("Audit trail"),
	auditEvents: () => browserUnavailable("Audit trail"),
	auditReplay: () => browserUnavailable("Audit trail"),
	auditVerify: () => browserUnavailable("Audit trail"),
	auditListTrails: () => browserUnavailable("Audit trail"),

	createPairRoom: () => browserUnavailable("Pair programming"),
	listPairRooms: () => browserUnavailable("Pair programming"),
	getPairRoom: () => browserUnavailable("Pair programming"),
	closePairRoom: () => browserUnavailable("Pair programming"),
	pairJoin: () => browserUnavailable("Pair programming"),
	pairLeave: () => browserUnavailable("Pair programming"),
	pairChat: () => browserUnavailable("Pair programming"),
	pairCursor: () => browserUnavailable("Pair programming"),
	pairEdit: () => browserUnavailable("Pair programming"),
	pairSuggestion: () => browserUnavailable("Pair programming"),
	pairOps: () => browserUnavailable("Pair programming"),
	subscribePairRoom: () => browserUnavailable("Pair programming"),
	unsubscribePairRoom: () => browserUnavailable("Pair programming"),
	onPairOpEvent: () => () => undefined,
	onPairStreamError: () => () => undefined,
};
