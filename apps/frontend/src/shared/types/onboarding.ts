/**
 * Onboarding Agent — Types for project onboarding guide generation.
 */

export type OnboardingSection =
	| "overview"
	| "setup"
	| "architecture"
	| "conventions"
	| "workflows"
	| "testing"
	| "deployment"
	| "troubleshooting";

export interface OnboardingStep {
	section: OnboardingSection;
	title: string;
	content: string;
	commands: string[];
	estimatedMinutes: number;
}

export interface OnboardingGuide {
	projectName: string;
	techStack: string[];
	steps: OnboardingStep[];
	totalEstimatedMinutes: number;
	generatedAt: string;
	summary: string;
}
