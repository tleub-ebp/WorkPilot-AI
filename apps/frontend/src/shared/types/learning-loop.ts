/**
 * Types for the Autonomous Agent Learning Loop feature.
 */

export type LearningPatternCategory =
  | 'tool_sequence'
  | 'prompt_strategy'
  | 'error_resolution'
  | 'qa_pattern'
  | 'code_structure';

export type LearningPatternType = 'success' | 'failure' | 'optimization';

export type LearningPatternSource = 'build_analysis' | 'qa_feedback' | 'error_recovery';

export interface LearningPattern {
  pattern_id: string;
  category: LearningPatternCategory;
  pattern_type: LearningPatternType;
  source: LearningPatternSource;
  description: string;
  confidence: number;
  occurrence_count: number;
  agent_phase: string;
  context_tags: string[];
  actionable_instruction: string;
  first_seen: string;
  last_seen: string;
  applied_count: number;
  success_after_apply: number;
  source_build_ids: string[];
  enabled: boolean;
  effectiveness_rate: number;
}

export interface LearningImprovementMetrics {
  qa_first_pass_rate: { before: number; after: number };
  avg_qa_iterations: { before: number; after: number };
  error_rate: { before: number; after: number };
}

export interface LearningSummary {
  total_patterns: number;
  by_category: Record<string, number>;
  by_phase: Record<string, number>;
  by_type: Record<string, number>;
  average_confidence: number;
  total_builds_analyzed: number;
  last_analyzed_at: string | null;
  improvement_metrics: LearningImprovementMetrics | null;
  enabled_count: number;
  disabled_count: number;
}

export interface LearningLoopReport {
  project_path: string;
  analyzed_builds: number;
  patterns_found: LearningPattern[];
  improvement_metrics: LearningImprovementMetrics | null;
  generated_at: string;
  analysis_model: string;
}

export interface LearningLoopCompleteResult {
  report: LearningLoopReport;
  summary: LearningSummary;
  patterns: LearningPattern[];
}
