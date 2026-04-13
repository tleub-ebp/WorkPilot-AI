/**
 * Carbon / Energy Profiler — Types for CO2 footprint tracking.
 */

export type ComputeSource = "llm_cloud" | "llm_local" | "ci_cd" | "local_dev";

export interface EnergyRecord {
	source: ComputeSource;
	provider: string;
	model: string;
	tokensIn: number;
	tokensOut: number;
	durationS: number;
	kwh: number;
	co2G: number;
	timestamp: string;
}

export interface CarbonReport {
	records: EnergyRecord[];
	totalKwh: number;
	totalCo2G: number;
	periodStart: string;
	periodEnd: string;
	byProvider: Record<string, number>;
	byModel: Record<string, number>;
	summary: string;
}
