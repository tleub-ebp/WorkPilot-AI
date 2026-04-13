/**
 * Compliance Evidence Collector — Types for audit evidence.
 */

export type ComplianceFramework =
	| "SOC2"
	| "ISO_27001"
	| "HIPAA"
	| "PCI_DSS"
	| "GDPR"
	| "CCPA";

export type EvidenceStatus =
	| "collected"
	| "verified"
	| "missing"
	| "expired";

export type EvidenceType =
	| "git_log"
	| "ci_cd_log"
	| "test_result"
	| "security_scan"
	| "code_review"
	| "policy_file"
	| "access_log";

export interface EvidenceItem {
	id: string;
	evidenceType: EvidenceType;
	framework: ComplianceFramework;
	controlId: string;
	title: string;
	description: string;
	status: EvidenceStatus;
	source: string;
}

export interface ComplianceReport {
	framework: ComplianceFramework;
	evidence: EvidenceItem[];
	coveragePercent: number;
	missingControls: string[];
	collectedCount: number;
	generatedAt: string;
	summary: string;
}
