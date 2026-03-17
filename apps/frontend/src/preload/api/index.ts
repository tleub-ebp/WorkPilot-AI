import { type ProjectAPI, createProjectAPI } from './project-api';
import { type TerminalAPI, createTerminalAPI } from './terminal-api';
import { type TaskAPI, createTaskAPI } from './task-api';
import { type SettingsAPI, createSettingsAPI } from './settings-api';
import { type FileAPI, createFileAPI } from './file-api';
import { type AgentAPI, createAgentAPI, type IdeationAPI, type InsightsAPI, type GitLabAPI, type AzureDevOpsAPI } from './agent-api';
import { type AppUpdateAPI, createAppUpdateAPI } from './app-update-api';
import { type GitHubAPI, createGitHubAPI } from './modules/github-api';
import { type DebugAPI, createDebugAPI } from './modules/debug-api';
import { type ClaudeCodeAPI, createClaudeCodeAPI } from './modules/claude-code-api';
import { type CopilotCliAPI, createCopilotCliAPI } from './modules/copilot-cli-api';
import { type CopilotOAuthAPI, createCopilotOAuthAPI } from './modules/copilot-oauth-api';
import { type McpAPI, createMcpAPI } from './modules/mcp-api';
import { type ProfileAPI, createProfileAPI } from './profile-api';
import { type ScreenshotAPI, createScreenshotAPI } from './screenshot-api';
import { type QueueAPI, createQueueAPI } from './queue-api';
import { type QualityAPI, createQualityAPI } from './modules/quality-api';
import { type NaturalLanguageGitAPI, createNaturalLanguageGitAPI } from './natural-language-git-api';
import type { PromptOptimizerAPI } from './modules/prompt-optimizer-api';
import { createPromptOptimizerAPI } from './modules/prompt-optimizer-api';
import type { CodePlaygroundAPI } from './modules/code-playground-api';
import { createCodePlaygroundAPI } from './modules/code-playground-api';
import type { ConflictPredictorAPI } from './modules/conflict-predictor-api';
import { createConflictPredictorAPI } from './modules/conflict-predictor-api';
import { type VoiceControlAPI, createVoiceControlAPI } from './modules/voice-control-api';
import type { AutoRefactorAPI } from './modules/auto-refactor-api';
import { createAutoRefactorAPI } from './modules/auto-refactor-api';
import { type SmartEstimationAPI, createSmartEstimationAPI } from './modules/smart-estimation-api';
import type { ContextAwareSnippetsAPI } from './modules/context-aware-snippets-api';
import { createContextAwareSnippetsAPI } from './modules/context-aware-snippets-api';
import type { AppEmulatorAPI } from './modules/app-emulator-api';
import { createAppEmulatorAPI } from './modules/app-emulator-api';
import type { LearningLoopAPI } from './modules/learning-loop-api';
import { createLearningLoopAPI } from './modules/learning-loop-api';
import type { MultiRepoAPI } from './modules/multi-repo-api';
import { createMultiRepoAPI } from './modules/multi-repo-api';
import type { ArchitectureVisualizerAPI } from './modules/architecture-visualizer-api';
import { createArchitectureVisualizerAPI } from './modules/architecture-visualizer-api';
import type { CodeMigrationAPI } from './modules/code-migration-api';
import { createCodeMigrationAPI } from './modules/code-migration-api';
import type { PerformanceProfilerAPI } from './modules/performance-profiler-api';
import { createPerformanceProfilerAPI } from './modules/performance-profiler-api';
import type { DocumentationAgentAPI } from './modules/documentation-agent-api';
import { createDocumentationAgentAPI } from './modules/documentation-agent-api';
import type { DecisionLoggerAPI } from './modules/decision-logger-api';
import { createDecisionLoggerAPI } from './modules/decision-logger-api';
import type { PairProgrammingAPI } from './modules/pair-programming-api';
import { createPairProgrammingAPI } from './modules/pair-programming-api';
import type { PipelineGeneratorAPI } from './modules/pipeline-generator-api';
import { createPipelineGeneratorAPI } from './modules/pipeline-generator-api';
import type { TeamSyncAPI } from './modules/team-sync-api';
import { createTeamSyncAPI } from './modules/team-sync-api';
import { invokeIpc } from './modules/ipc-utils';
import type { IPCResult, UsageSnapshot } from '../../shared/types';

export interface ElectronAPI extends
  ProjectAPI,
  TerminalAPI,
  TaskAPI,
  SettingsAPI,
  FileAPI,
  AgentAPI,
  IdeationAPI,
  InsightsAPI,
  AppUpdateAPI,
  GitLabAPI,
  AzureDevOpsAPI,
  DebugAPI,
  ClaudeCodeAPI,
  CopilotCliAPI,
  CopilotOAuthAPI,
  McpAPI,
  ProfileAPI,
  ScreenshotAPI,
  NaturalLanguageGitAPI,
  PromptOptimizerAPI,
  CodePlaygroundAPI,
  ConflictPredictorAPI,
  VoiceControlAPI,
  SmartEstimationAPI,
  ContextAwareSnippetsAPI,
  AppEmulatorAPI,
  LearningLoopAPI,
  MultiRepoAPI,
  ArchitectureVisualizerAPI,
  CodeMigrationAPI,
  PerformanceProfilerAPI,
  DocumentationAgentAPI,
  DecisionLoggerAPI,
  PairProgrammingAPI,
  PipelineGeneratorAPI,
  TeamSyncAPI {
  github: GitHubAPI;
  /** Queue routing API for rate limit recovery */
  queue: QueueAPI;
  /** Code quality analysis API */
  quality: QualityAPI;
  createClaudeProfileDirectory: (profileName: string) => Promise<{ success: boolean; data?: string; error?: string }>;
  requestUsageUpdate: (providerName?: string) => Promise<IPCResult<UsageSnapshot | null>>;
  /** Get GitHub CLI status for Copilot authentication */
  getGithubCliStatus: () => Promise<IPCResult<{ available: boolean; isAuth?: boolean; username?: string }>>;
  /** LLM Provider operations */
  selectProvider: (provider: string) => Promise<IPCResult<string>>;
  getSelectedProvider: () => Promise<IPCResult<string | null>>;
  /** Test GitHub connection for remote configuration */
  testGitHubConnection: (config: { repo: string; token: string }) => Promise<{ success: boolean; status?: number; error?: string }>;
  /** Detect Windsurf API key from local IDE installation (state.vscdb) + account info */
  detectWindsurfToken: () => Promise<{ success: boolean; apiKey?: string; userName?: string; planName?: string; usageInfo?: { usedMessages: number; totalMessages: number; usedFlowActions: number; totalFlowActions: number }; error?: string }>;
  /** Check Claude OAuth status from CLI config files on disk */
  checkClaudeOAuth: () => Promise<{ isAuthenticated: boolean; profileName?: string }>;
  /** Check OpenAI Codex CLI OAuth status from config files on disk */
  checkOpenAICodexOAuth: () => Promise<{ isAuthenticated: boolean; profileName?: string }>;
}

export const createElectronAPI = (): ElectronAPI => {
  return {
    ...createProjectAPI(),
    ...createTerminalAPI(),
    ...createTaskAPI(),
    ...createSettingsAPI(),
    ...createFileAPI(),
    ...createAgentAPI(),
    ...createAppUpdateAPI(),
    ...createDebugAPI(),
    ...createClaudeCodeAPI(),
    ...createCopilotCliAPI(),
    ...createCopilotOAuthAPI(),
    ...createMcpAPI(),
    ...createProfileAPI(),
    ...createScreenshotAPI(),
    ...createNaturalLanguageGitAPI(),
    ...createPromptOptimizerAPI(),
    ...createCodePlaygroundAPI(),
    ...createConflictPredictorAPI(),
    ...createVoiceControlAPI(),
    ...createSmartEstimationAPI(),
    ...createContextAwareSnippetsAPI(),
    ...createAppEmulatorAPI(),
    ...createLearningLoopAPI(),
    ...createMultiRepoAPI(),
    ...createArchitectureVisualizerAPI(),
    ...createCodeMigrationAPI(),
    ...createPerformanceProfilerAPI(),
    ...createDocumentationAgentAPI(),
    ...createDecisionLoggerAPI(),
    ...createPairProgrammingAPI(),
    ...createPipelineGeneratorAPI(),
    ...createTeamSyncAPI(),
    github: createGitHubAPI(),
    queue: createQueueAPI(),  // Queue routing for rate limit recovery
    quality: createQualityAPI(),  // Code quality analysis
    createClaudeProfileDirectory: (profileName: string) => invokeIpc<{ success: boolean; data?: string; error?: string }>('claude:profileCreateDir', profileName),
    requestUsageUpdate: (providerName?: string) => invokeIpc<IPCResult<UsageSnapshot | null>>('claude:usageRequest', providerName),
    getGithubCliStatus: () => invokeIpc<IPCResult<{ available: boolean; isAuth?: boolean; username?: string }>>('copilotCli:getStatus'),
    selectProvider: (provider: string) => invokeIpc<IPCResult<string>>('provider:select', provider),
    getSelectedProvider: () => invokeIpc<IPCResult<string | null>>('provider:getSelected'),
    testGitHubConnection: (config: { repo: string; token: string }) => invokeIpc<{ success: boolean; status?: number; error?: string }>('github:testConnection', config),
    detectWindsurfToken: () => invokeIpc<{ success: boolean; apiKey?: string; userName?: string; error?: string }>('credential:detectWindsurfToken'),
    checkClaudeOAuth: () => invokeIpc<{ isAuthenticated: boolean; profileName?: string }>('credential:checkClaudeOAuth'),
    checkOpenAICodexOAuth: () => invokeIpc<{ isAuthenticated: boolean; profileName?: string }>('credential:checkOpenAICodexOAuth'),
  };
};

// Export individual API creators for potential use in tests or specialized contexts
// Note: IdeationAPI, InsightsAPI, GitLabAPI, and AzureDevOpsAPI are included in AgentAPI
export { createProjectAPI } from './project-api';
export { createTerminalAPI } from './terminal-api';
export { createTaskAPI } from './task-api';
export { createSettingsAPI } from './settings-api';
export { createFileAPI } from './file-api';
export { createAgentAPI } from './agent-api';
export { createAppUpdateAPI } from './app-update-api';
export { createProfileAPI } from './profile-api';
export { createGitHubAPI } from './modules/github-api';
export { createDebugAPI } from './modules/debug-api';
export { createClaudeCodeAPI } from './modules/claude-code-api';
export { createCopilotCliAPI } from './modules/copilot-cli-api';
export { createMcpAPI } from './modules/mcp-api';
export { createScreenshotAPI } from './screenshot-api';
export { createQueueAPI } from './queue-api';
export { createQualityAPI } from './modules/quality-api';
export { createAutoRefactorAPI } from './modules/auto-refactor-api';
export { createNaturalLanguageGitAPI } from './natural-language-git-api';
export { createPromptOptimizerAPI } from './modules/prompt-optimizer-api';
export { createCodePlaygroundAPI } from './modules/code-playground-api';
export { createConflictPredictorAPI } from './modules/conflict-predictor-api';
export { createSmartEstimationAPI } from './modules/smart-estimation-api';
export { createContextAwareSnippetsAPI } from './modules/context-aware-snippets-api';
export { createVoiceControlAPI } from './modules/voice-control-api';
export { createAppEmulatorAPI } from './modules/app-emulator-api';

export type { ProjectAPI } from './project-api';
export type { TerminalAPI } from './terminal-api';
export type { TaskAPI } from './task-api';
export type { SettingsAPI } from './settings-api';
export type { FileAPI } from './file-api';
export type { AgentAPI, IdeationAPI, InsightsAPI, GitLabAPI, AzureDevOpsAPI } from './agent-api';
export type { AppUpdateAPI } from './app-update-api';
export type { ProfileAPI } from './profile-api';
export type { GitHubAPI } from './modules/github-api';
export type { DebugAPI } from './modules/debug-api';
export type { ClaudeCodeAPI } from './modules/claude-code-api';
export type { CopilotCliAPI } from './modules/copilot-cli-api';
export type { McpAPI } from './modules/mcp-api';
export type { ScreenshotAPI } from './screenshot-api';
export type { QueueAPI } from './queue-api';
export type { QualityAPI } from './modules/quality-api';
export type { NaturalLanguageGitAPI } from './natural-language-git-api';
export type { SmartEstimationAPI } from './modules/smart-estimation-api';
export type { ContextAwareSnippetsAPI } from './modules/context-aware-snippets-api';
export type { VoiceControlAPI } from './modules/voice-control-api';
export type { AppEmulatorAPI } from './modules/app-emulator-api';
export type { MultiRepoAPI } from './modules/multi-repo-api';
export { createMultiRepoAPI } from './modules/multi-repo-api';
export { createArchitectureVisualizerAPI } from './modules/architecture-visualizer-api';
export { createCodeMigrationAPI } from './modules/code-migration-api';
export { createPerformanceProfilerAPI } from './modules/performance-profiler-api';
export { createDocumentationAgentAPI } from './modules/documentation-agent-api';
export { createDecisionLoggerAPI } from './modules/decision-logger-api';
export type { ArchitectureVisualizerAPI } from './modules/architecture-visualizer-api';
export type { CodeMigrationAPI } from './modules/code-migration-api';
export type { PerformanceProfilerAPI } from './modules/performance-profiler-api';
export type { DocumentationAgentAPI } from './modules/documentation-agent-api';
export type { DecisionLoggerAPI } from './modules/decision-logger-api';
export { createPairProgrammingAPI } from './modules/pair-programming-api';
export type { PairProgrammingAPI } from './modules/pair-programming-api';