/**
 * Model and agent profile constants
 * Claude models, thinking levels, memory backends, and agent profiles
 */

import type { AgentProfile, PhaseModelConfig, FeatureModelConfig, FeatureThinkingConfig } from '../types/settings';

// ============================================
// Provider Model Catalog
// ============================================

export interface ProviderModel {
  value: string;       // Model ID as sent to the API
  label: string;       // Human-readable label
  tier: 'flagship' | 'standard' | 'fast' | 'local'; // Capability tier
  supportsThinking?: boolean; // Extended thinking / reasoning support
}

/** Models grouped by provider. Keys match provider names used in ProviderContext / provider_api.py */
export const PROVIDER_MODELS_MAP: Record<string, ProviderModel[]> = {
  // ---- Anthropic (Claude) ----
  anthropic: [
    { value: 'claude-opus-4-6',           label: 'Claude Opus 4.6',        tier: 'flagship', supportsThinking: true },
    { value: 'claude-sonnet-4-6',        label: 'Claude Sonnet 4.6',      tier: 'standard', supportsThinking: true },
    { value: 'claude-haiku-4-6',         label: 'Claude Haiku 4.6',       tier: 'fast',     supportsThinking: false },
    { value: 'claude-opus-4-5-20251101',  label: 'Claude Opus 4.5',        tier: 'flagship', supportsThinking: true },
    { value: 'claude-sonnet-4-5-20250929',label: 'Claude Sonnet 4.5',      tier: 'standard', supportsThinking: true },
    { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5',       tier: 'fast',     supportsThinking: false },
  ],

  // ---- GitHub Copilot ----
  copilot: [
    { value: 'gpt-5.4',              label: 'GPT-5.4 (Copilot)',            tier: 'flagship' },
    { value: 'gpt-5.3',              label: 'GPT-5.3 (Copilot)',            tier: 'flagship' },
    { value: 'o4',                   label: 'o4 (Copilot)',                 tier: 'flagship', supportsThinking: true },
    { value: 'gpt-5.2',              label: 'GPT-5.2 (Copilot)',            tier: 'flagship' },
    { value: 'gpt-5',                label: 'GPT-5 (Copilot)',              tier: 'flagship' },
    { value: 'o3',                   label: 'o3 (Copilot)',                 tier: 'flagship', supportsThinking: true },
    { value: 'claude-opus-4-6',      label: 'Claude Opus 4.6 (Copilot)',    tier: 'flagship', supportsThinking: true },
    { value: 'claude-sonnet-4-6',    label: 'Claude Sonnet 4.6 (Copilot)',  tier: 'standard', supportsThinking: true },
    { value: 'gpt-4o',               label: 'GPT-4o (Copilot)',             tier: 'standard' },
    { value: 'o4-mini',              label: 'o4-mini (Copilot)',            tier: 'standard', supportsThinking: true },
    { value: 'o3-mini',              label: 'o3-mini (Copilot)',            tier: 'standard', supportsThinking: true },
    { value: 'claude-sonnet-4-5',    label: 'Claude Sonnet 4.5 (Copilot)',  tier: 'standard', supportsThinking: true },
    { value: 'gpt-4o-mini',          label: 'GPT-4o mini (Copilot)',        tier: 'fast' },
  ],

  // ---- OpenAI ----
  openai: [
    { value: 'gpt-5.4',       label: 'GPT-5.4',           tier: 'flagship' },
    { value: 'gpt-5.3',       label: 'GPT-5.3',           tier: 'flagship' },
    { value: 'gpt-5.2',       label: 'GPT-5.2',           tier: 'flagship' },
    { value: 'gpt-5',         label: 'GPT-5',              tier: 'flagship' },
    { value: 'o4',            label: 'o4',                  tier: 'flagship', supportsThinking: true },
    { value: 'o4-mini',       label: 'o4-mini',            tier: 'standard', supportsThinking: true },
    { value: 'o3',            label: 'o3',                  tier: 'flagship', supportsThinking: true },
    { value: 'o3-mini',       label: 'o3-mini',            tier: 'standard', supportsThinking: true },
    { value: 'gpt-4o',        label: 'GPT-4o',             tier: 'standard' },
    { value: 'gpt-4o-mini',   label: 'GPT-4o mini',        tier: 'fast' },
    { value: 'gpt-4-turbo',   label: 'GPT-4 Turbo',        tier: 'standard' },
  ],

  // ---- Google Gemini ----
  google: [
    { value: 'gemini-3.1-pro',        label: 'Gemini 3.1 Pro',         tier: 'flagship', supportsThinking: true },
    { value: 'gemini-3-flash',         label: 'Gemini 3 Flash',          tier: 'flagship' },
    { value: 'gemini-3.1-flash-lite',  label: 'Gemini 3.1 Flash-Lite',   tier: 'standard' },
    { value: 'gemini-2.5-pro',        label: 'Gemini 2.5 Pro',         tier: 'flagship', supportsThinking: true },
    { value: 'gemini-2.5-flash',      label: 'Gemini 2.5 Flash',       tier: 'fast' },
    { value: 'gemini-2.0-flash-thinking', label: 'Gemini 2.0 Flash Thinking', tier: 'standard', supportsThinking: true },
    { value: 'gemini-1.5-pro',        label: 'Gemini 1.5 Pro',         tier: 'standard' },
    { value: 'gemini-1.5-flash',      label: 'Gemini 1.5 Flash',       tier: 'fast' },
  ],

  // ---- Mistral AI ----
  mistral: [
    { value: 'mistral-large-3',   label: 'Mistral Large 3',     tier: 'flagship' },
    { value: 'ministral-3-14b',   label: 'Ministral 3 14B',      tier: 'standard' },
    { value: 'ministral-3-8b',    label: 'Ministral 3 8B',       tier: 'standard' },
    { value: 'ministral-3-3b',    label: 'Ministral 3 3B',       tier: 'fast' },
    { value: 'mistral-medium-3',  label: 'Mistral Medium 3',    tier: 'standard' },
    { value: 'mistral-small-3',   label: 'Mistral Small 3',     tier: 'fast' },
    { value: 'codestral',         label: 'Codestral',           tier: 'standard' },
    { value: 'mistral-7b',        label: 'Mistral 7B',          tier: 'fast' },
  ],

  // ---- DeepSeek ----
  deepseek: [
    { value: 'deepseek-v3.2',            label: 'DeepSeek V3.2',            tier: 'flagship' },
    { value: 'deepseek-r2',            label: 'DeepSeek R2',            tier: 'flagship', supportsThinking: true },
    { value: 'deepseek-v3',            label: 'DeepSeek V3',            tier: 'standard' },
    { value: 'deepseek-r1',            label: 'DeepSeek R1',            tier: 'standard', supportsThinking: true },
    { value: 'deepseek-coder-v2',      label: 'DeepSeek Coder V2',      tier: 'standard' },
  ],

  // ---- Grok (xAI) ----
  grok: [
    { value: 'grok-2',            label: 'Grok 2',              tier: 'flagship', supportsThinking: true },
    { value: 'grok-2-mini',       label: 'Grok 2 Mini',         tier: 'standard' },
    { value: 'grok-beta',         label: 'Grok Beta',           tier: 'standard' },
  ],

  // ---- Meta (LLaMA) ----
  meta: [
    { value: 'meta-llama/llama-4-scout',  label: 'Llama 4 Scout',      tier: 'flagship' },
    { value: 'meta-llama/llama-3.3-70b',  label: 'Llama 3.3 70B',      tier: 'standard' },
    { value: 'meta-llama/llama-3.1-70b',  label: 'Llama 3.1 70B',      tier: 'standard' },
    { value: 'meta-llama/llama-3.1-8b',   label: 'Llama 3.1 8B',       tier: 'fast' },
  ],

  // ---- AWS Bedrock ----
  aws: [
    { value: 'anthropic.claude-opus-4-6-v1',    label: 'Claude Opus 4.6 (Bedrock)',   tier: 'flagship', supportsThinking: true },
    { value: 'anthropic.claude-sonnet-4-6-v1',  label: 'Claude Sonnet 4.6 (Bedrock)', tier: 'standard', supportsThinking: true },
    { value: 'anthropic.claude-sonnet-4-5-v1',  label: 'Claude Sonnet 4.5 (Bedrock)', tier: 'standard', supportsThinking: true },
    { value: 'amazon.titan-text-premier-v1',    label: 'Amazon Titan Premier',         tier: 'standard' },
    { value: 'meta.llama3-70b-instruct-v1',     label: 'Llama 3 70B (Bedrock)',        tier: 'standard' },
  ],

  // ---- Ollama / LLM local ----
  ollama: [
    { value: 'llama3.3',         label: 'Llama 3.3',            tier: 'local' },
    { value: 'llama3.2',         label: 'Llama 3.2',            tier: 'local' },
    { value: 'llama3.1',         label: 'Llama 3.1',            tier: 'local' },
    { value: 'mistral-large-3',  label: 'Mistral Large 3',     tier: 'local' },
    { value: 'mistral',          label: 'Mistral',              tier: 'local' },
    { value: 'mistral-large',    label: 'Mistral Large',        tier: 'local' },
    { value: 'deepseek-v3.2',    label: 'DeepSeek V3.2',        tier: 'local' },
    { value: 'deepseek-r2',      label: 'DeepSeek R2',          tier: 'local', supportsThinking: true },
    { value: 'deepseek-r1',      label: 'DeepSeek R1',          tier: 'local', supportsThinking: true },
    { value: 'deepseek-coder-v2', label: 'DeepSeek Coder V2',   tier: 'local' },
    { value: 'qwen2.5-coder',    label: 'Qwen 2.5 Coder',       tier: 'local' },
    { value: 'qwen2.5',          label: 'Qwen 2.5',             tier: 'local' },
    { value: 'phi4',             label: 'Phi-4',                tier: 'local' },
    { value: 'gemma3',           label: 'Gemma 3',              tier: 'local' },
    { value: 'gemma2',           label: 'Gemma 2',              tier: 'local' },
    { value: 'codellama',        label: 'CodeLlama',            tier: 'local' },
    { value: 'yi',               label: 'Yi',                   tier: 'local' },
    { value: 'mixtral',          label: 'Mixtral',              tier: 'local' },
    { value: 'vicuna',           label: 'Vicuna',               tier: 'local' },
    { value: 'wizardlm',         label: 'WizardLM',             tier: 'local' },
    { value: 'solar',            label: 'Solar Pro',            tier: 'local' },
    { value: 'custom',           label: 'Autre (saisie libre)', tier: 'local' },
  ],

  // ---- Custom/Enterprise API ----
  custom: [
    { value: 'custom-model-1', label: 'Custom Model 1', tier: 'flagship', supportsThinking: true },
    { value: 'custom-model-2', label: 'Custom Model 2', tier: 'standard', supportsThinking: true },
    { value: 'custom-model-3', label: 'Custom Model 3', tier: 'fast' },
    { value: 'custom', label: 'Autre (saisie libre)', tier: 'local', supportsThinking: true },
  ],

  // ---- Windsurf (Codeium) ----
  windsurf: [
    { value: 'windsurf-codestral', label: 'Windsurf Codestral', tier: 'flagship' },
    { value: 'windsurf-sonnet', label: 'Windsurf Sonnet', tier: 'standard' },
    { value: 'windsurf-haiku', label: 'Windsurf Haiku', tier: 'fast' },
    { value: 'windsurf-custom', label: 'Windsurf Custom', tier: 'standard' },
  ],
};

// Alias for legacy providers listed in provider_api.py
PROVIDER_MODELS_MAP['claude'] = PROVIDER_MODELS_MAP['anthropic'];

/** Returns models for the currently selected provider, falling back to anthropic */
export function getModelsForProvider(provider: string): ProviderModel[] {
  return PROVIDER_MODELS_MAP[provider] ?? PROVIDER_MODELS_MAP['anthropic'];
}

/** Returns the default (flagship) model ID for a given provider */
export function getDefaultModelForProvider(provider: string): string {
  const models = getModelsForProvider(provider);
  const flagship = models.find(m => m.tier === 'flagship') ?? models[0];
  return flagship?.value ?? '';
}

/** Returns whether the selected provider supports extended thinking */
export function providerSupportsThinking(provider: string): boolean {
  return ['anthropic', 'openai', 'google', 'deepseek', 'mistral', 'ollama', 'copilot', 'custom', 'grok', 'windsurf'].includes(provider);
}

// ============================================
// Available Models (legacy – Claude only, kept for backward compatibility)
// ============================================

export const AVAILABLE_MODELS = [
  { value: 'opus', label: 'Claude Opus 4.6' },
  { value: 'sonnet', label: 'Claude Sonnet 4.6' },
  { value: 'haiku', label: 'Claude Haiku 4.6' },
  { value: 'opus-4-5', label: 'Claude Opus 4.5' },
  { value: 'sonnet-4-5', label: 'Claude Sonnet 4.5' },
  { value: 'haiku-4-5', label: 'Claude Haiku 4.5' },
] as const;

// Maps model shorthand to actual Claude model IDs
export const MODEL_ID_MAP: Record<string, string> = {
  opus: 'claude-opus-4-6',
  sonnet: 'claude-sonnet-4-6',
  haiku: 'claude-haiku-4-6',
  'opus-4-5': 'claude-opus-4-5-20251101',
  'sonnet-4-5': 'claude-sonnet-4-5-20250929',
  'haiku-4-5': 'claude-haiku-4-5-20251001'
} as const;

// Maps thinking levels to budget tokens (null = no extended thinking)
export const THINKING_BUDGET_MAP: Record<string, number | null> = {
  none: null,
  low: 1024,
  medium: 4096,
  high: 16384,
  ultrathink: 63999 // Maximum reasoning depth (API requires max_tokens >= budget + 1, so 63999 + 1 = 64000 limit)
} as const;

// ============================================
// Thinking Levels
// ============================================

// Thinking levels for Claude model (budget token allocation)
export const THINKING_LEVELS = [
  { value: 'none', label: 'None', description: 'No extended thinking' },
  { value: 'low', label: 'Low', description: 'Brief consideration' },
  { value: 'medium', label: 'Medium', description: 'Moderate analysis' },
  { value: 'high', label: 'High', description: 'Deep thinking' },
  { value: 'ultrathink', label: 'Ultra Think', description: 'Maximum reasoning depth' }
] as const;

// ============================================
// Agent Profiles - Phase Configurations
// ============================================

// Phase configurations for each preset profile
// Each profile has its own default phase models and thinking levels

// Auto (Optimized) - Opus with optimized thinking per phase
export const AUTO_PHASE_MODELS: PhaseModelConfig = {
  spec: 'opus',
  planning: 'opus',
  coding: 'opus',
  qa: 'opus'
};

export const AUTO_PHASE_THINKING: import('../types/settings').PhaseThinkingConfig = {
  spec: 'ultrathink',   // Deep thinking for comprehensive spec creation
  planning: 'high',     // High thinking for planning complex features
  coding: 'low',        // Faster coding iterations
  qa: 'low'             // Efficient QA review
};

// Complex Tasks - Opus with ultrathink across all phases
export const COMPLEX_PHASE_MODELS: PhaseModelConfig = {
  spec: 'opus',
  planning: 'opus',
  coding: 'opus',
  qa: 'opus'
};

export const COMPLEX_PHASE_THINKING: import('../types/settings').PhaseThinkingConfig = {
  spec: 'ultrathink',
  planning: 'ultrathink',
  coding: 'ultrathink',
  qa: 'ultrathink'
};

// Balanced - Sonnet with medium thinking across all phases
export const BALANCED_PHASE_MODELS: PhaseModelConfig = {
  spec: 'sonnet',
  planning: 'sonnet',
  coding: 'sonnet',
  qa: 'sonnet'
};

export const BALANCED_PHASE_THINKING: import('../types/settings').PhaseThinkingConfig = {
  spec: 'medium',
  planning: 'medium',
  coding: 'medium',
  qa: 'medium'
};

// Quick Edits - Haiku with low thinking across all phases
export const QUICK_PHASE_MODELS: PhaseModelConfig = {
  spec: 'haiku',
  planning: 'haiku',
  coding: 'haiku',
  qa: 'haiku'
};

export const QUICK_PHASE_THINKING: import('../types/settings').PhaseThinkingConfig = {
  spec: 'low',
  planning: 'low',
  coding: 'low',
  qa: 'low'
};

// Default phase configuration (used for fallback, matches 'Balanced' profile for cost-effectiveness)
export const DEFAULT_PHASE_MODELS: PhaseModelConfig = BALANCED_PHASE_MODELS;
export const DEFAULT_PHASE_THINKING: import('../types/settings').PhaseThinkingConfig = BALANCED_PHASE_THINKING;

// ============================================
// Feature Settings (Non-Pipeline Features)
// ============================================

// Default feature model configuration (for insights, ideation, roadmap, github, utility).
// Values must match the `value` field of entries in PROVIDER_MODELS_MAP['anthropic'].
export const DEFAULT_FEATURE_MODELS: FeatureModelConfig = {
  insights: 'claude-sonnet-4-6',              // Fast, responsive chat with latest model
  ideation: 'claude-opus-4-6',              // Creative ideation benefits from Opus
  roadmap: 'claude-opus-4-6',              // Strategic planning benefits from Opus
  'natural-language-git': 'claude-sonnet-4-6', // Natural language Git commands
  githubIssues: 'claude-opus-4-6',         // Issue triage and analysis benefits from Opus
  githubPrs: 'claude-opus-4-6',            // PR review benefits from thorough Opus analysis
  utility: 'claude-haiku-4-6',             // Fast utility operations (commit messages, merge resolution)
  promptOptimizer: 'claude-sonnet-4-6',    // Balanced prompt optimization
  testGenerator: 'claude-sonnet-4-6',     // Balanced test generation for comprehensive coverage
  codeReview: 'claude-opus-4-6',          // Code review benefits from thorough Opus analysis
  voiceControl: 'claude-haiku-4-6'        // Fast voice control operations
};

// Default feature thinking configuration
export const DEFAULT_FEATURE_THINKING: FeatureThinkingConfig = {
  insights: 'medium',     // Balanced thinking for chat
  ideation: 'high',       // Deep thinking for creative ideas
  roadmap: 'high',        // Strategic thinking for roadmap
  'natural-language-git': 'medium', // Natural language Git commands
  githubIssues: 'medium', // Moderate thinking for issue analysis
  githubPrs: 'medium',    // Moderate thinking for PR review
  utility: 'low',         // Fast thinking for utility operations
  promptOptimizer: 'medium', // Balanced thinking for prompt optimization
  testGenerator: 'medium',  // Balanced thinking for test generation
  codeReview: 'medium',    // Balanced thinking for code review
  voiceControl: 'low'      // Fast thinking for voice control
};

// Feature labels for UI display
export const FEATURE_LABELS: Record<keyof FeatureModelConfig, { label: string; description: string }> = {
  insights: { label: 'Insights Chat', description: 'Ask questions about your codebase' },
  ideation: { label: 'Ideation', description: 'Generate feature ideas and improvements' },
  roadmap: { label: 'Roadmap', description: 'Create strategic feature roadmaps' },
  'natural-language-git': { label: 'Natural Language Git', description: 'Execute Git commands using natural language' },
  githubIssues: { label: 'GitHub Issues', description: 'Automated issue triage and labeling' },
  githubPrs: { label: 'GitHub PR Review', description: 'AI-powered pull request reviews' },
  utility: { label: 'Utility', description: 'Commit messages and merge conflict resolution' },
  promptOptimizer: { label: 'Prompt Optimizer', description: 'AI-powered prompt enhancement with project context' },
  testGenerator: { label: 'Test Generation Agent', description: 'AI-powered test generation and coverage analysis' },
  codeReview: { label: 'Code Review Agent', description: 'AI-powered code review and quality analysis' },
  voiceControl: { label: 'Voice Control', description: 'Voice-activated development commands' }
};

// Default agent profiles for preset model/thinking configurations
// All profiles have per-phase configuration for full customization
export const DEFAULT_AGENT_PROFILES: AgentProfile[] = [
  {
    id: 'auto',
    name: 'Auto (Optimized)',
    description: 'Uses Opus across all phases with optimized thinking levels',
    model: 'opus',
    thinkingLevel: 'high',
    icon: 'Sparkles',
    phaseModels: AUTO_PHASE_MODELS,
    phaseThinking: AUTO_PHASE_THINKING
  },
  {
    id: 'complex',
    name: 'Complex Tasks',
    description: 'For intricate, multi-step implementations requiring deep analysis',
    model: 'opus',
    thinkingLevel: 'ultrathink',
    icon: 'Brain',
    phaseModels: COMPLEX_PHASE_MODELS,
    phaseThinking: COMPLEX_PHASE_THINKING
  },
  {
    id: 'balanced',
    name: 'Balanced',
    description: 'Good balance of speed and quality for most tasks',
    model: 'sonnet',
    thinkingLevel: 'medium',
    icon: 'Scale',
    phaseModels: BALANCED_PHASE_MODELS,
    phaseThinking: BALANCED_PHASE_THINKING
  },
  {
    id: 'quick',
    name: 'Quick Edits',
    description: 'Fast iterations for simple changes and quick fixes',
    model: 'haiku',
    thinkingLevel: 'low',
    icon: 'Zap',
    phaseModels: QUICK_PHASE_MODELS,
    phaseThinking: QUICK_PHASE_THINKING
  }
];

// ============================================
// Memory Backends
// ============================================

export const MEMORY_BACKENDS = [
  { value: 'file', label: 'File-based (default)' },
  { value: 'graphiti', label: 'Graphiti (LadybugDB)' }
] as const;