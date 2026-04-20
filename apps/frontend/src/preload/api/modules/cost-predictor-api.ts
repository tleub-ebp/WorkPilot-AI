/**
 * Cost Predictor API — renderer-side bridge for ex-ante cost prediction.
 */

import { invokeIpc } from "./ipc-utils";

export interface SpecFootprint {
	subtasks: number;
	files_touched: number;
	lines_in_scope: number;
	spec_id: string;
}

export interface CostPrediction {
	provider: string;
	model: string;
	input_tokens: number;
	output_tokens: number;
	thinking_tokens: number;
	total_tokens: number;
	expected_qa_iterations: number;
	point_cost_usd: number;
	low_cost_usd: number;
	high_cost_usd: number;
	notes: string[];
}

export interface PredictionReport {
	footprint: SpecFootprint;
	selected: CostPrediction;
	alternatives: CostPrediction[];
	history_sample_count: number;
	confidence_band: number;
}

export interface CostPredictorRunOptions {
	projectPath: string;
	specId: string;
	provider?: string;
	model?: string;
	compare?: string;
	thinking?: boolean;
}

export interface CostPredictorAPI {
	runCostPrediction: (
		options: CostPredictorRunOptions,
	) => Promise<{ report: PredictionReport }>;
}

export const createCostPredictorAPI = (): CostPredictorAPI => ({
	runCostPrediction: (options) =>
		invokeIpc<{ report: PredictionReport }>("costPredictor:run", options),
});
