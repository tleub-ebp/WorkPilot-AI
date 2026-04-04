/**
 * Browser Agent Types
 *
 * Feature #20 — Built-in Browser Agent for testing, scraping, and visual validation.
 */

// ── Enums ──────────────────────────────────────────────────

export type BrowserAgentTab = "browser" | "visual-regression" | "test-runner";

export type TestStatus = "passed" | "failed" | "skipped" | "error";

export type BrowserStatus =
	| "idle"
	| "launching"
	| "navigating"
	| "ready"
	| "error";

// ── Core Models ────────────────────────────────────────────

export interface BrowserAgentStats {
	totalTests: number;
	passRate: number;
	screenshotsCaptured: number;
	regressionsDetected: number;
}

export interface ScreenshotInfo {
	name: string;
	path: string;
	url: string;
	timestamp: string;
	width: number;
	height: number;
}

export interface BaselineInfo {
	name: string;
	path: string;
	createdAt: string;
	width: number;
	height: number;
}

export interface ComparisonResult {
	name: string;
	baselinePath: string;
	currentPath: string;
	diffImagePath: string | null;
	matchPercentage: number;
	diffPixels: number;
	passed: boolean;
	threshold: number;
}

export interface TestResult {
	name: string;
	path: string;
	status: TestStatus;
	durationMs: number;
	errorMessage: string | null;
	screenshotPath: string | null;
}

export interface TestRunResult {
	total: number;
	passed: number;
	failed: number;
	skipped: number;
	durationMs: number;
	results: TestResult[];
}

// ── Dashboard ──────────────────────────────────────────────

export interface BrowserAgentDashboardData {
	stats: BrowserAgentStats;
	screenshots: ScreenshotInfo[];
	baselines: BaselineInfo[];
	comparisons: ComparisonResult[];
	recentTestRun: TestRunResult | null;
}
