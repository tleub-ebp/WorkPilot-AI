/**
 * IPC Handlers Module Index
 *
 * This module exports a single setup function that registers all IPC handlers
 * organized by domain into separate handler modules.
 */

import type { BrowserWindow } from 'electron';
import { AgentManager } from '../agent';
import { TerminalManager } from '../terminal-manager';
import { PythonEnvManager } from '../python-env-manager';

// Import all handler registration functions for internal use
import { registerProjectHandlers } from './project-handlers';
import { registerTaskHandlers } from './task-handlers';
import { registerTerminalHandlers } from './terminal-handlers';
import { registerAgenteventsHandlers } from './agent-events-handlers';
import { registerSettingsHandlers } from './settings-handlers';
import { registerFileHandlers } from './file-handlers';
import { registerRoadmapHandlers } from './roadmap-handlers';
import { registerContextHandlers } from './context-handlers';
import { registerEnvHandlers } from './env-handlers';
import { registerLinearHandlers } from './linear-handlers';
import { registerAzureDevOpsHandlers } from './azure-devops-handlers';
import { registerPRDetailsHandlers } from './pr-details-handlers';
import { registerJiraHandlers } from './jira-handlers';
import { registerGithubHandlers } from './github-handlers';
import { registerGitlabHandlers } from './gitlab-handlers';
import { registerIdeationHandlers } from './ideation-handlers';
import { registerChangelogHandlers } from './changelog-handlers';
import { registerInsightsHandlers } from './insights-handlers';
import { registerMemoryHandlers } from './memory-handlers';
import { registerAppUpdateHandlers } from './app-update-handlers';
import { registerDebugHandlers } from './debug-handlers';
import { registerClaudeCodeHandlers } from './claude-code-handlers';
import { registerCopilotCliHandlers } from './copilot-cli-handlers';
import { registerCopilotOAuthHandlers } from './copilot-oauth-handlers';
import { registerMcpHandlers } from './mcp-handlers';
import { registerProfileHandlers } from './profile-handlers';
import { registerScreenshotHandlers } from './screenshot-handlers';
import { registerTerminalWorktreeIpcHandlers } from './terminal';
import { notificationService } from '../notification-service';
import { setupQualityHandlers } from './quality-handlers';
import { registerPromptOptimizerHandlers } from './prompt-optimizer-handlers';
import { registerCredentialHandlers } from './credential-handlers';
import { registerGitHubCopilotHandlers } from './github-copilot-handlers';
import { setupNaturalLanguageGitHandlers } from './natural-language-git-handlers';
import { setupSmartEstimationHandlers } from './smart-estimation-handlers';
import { setupConflictPredictorHandlers } from './conflict-predictor-handlers';
import { registerVoiceControlHandlers, setupVoiceControlEvents } from './voice-control-handlers';
import { registerAppEmulatorHandlers } from './app-emulator-handlers';
import { registerLearningLoopHandlers } from './learning-loop-handlers';
import { registerMcpMarketplaceHandlers } from './mcp-marketplace-handlers';
import { registerMultiRepoHandlers } from './multi-repo-handlers';
import { registerSelfHealingHandlers } from './self-healing-handlers';
import { registerBrowserAgentHandlers } from './browser-agent-handlers';
import { registerArchitectureVisualizerHandlers, setupArchitectureVisualizerEventForwarding } from './architecture-visualizer-handlers';
import { registerCodeMigrationHandlers, setupCodeMigrationEventForwarding } from './code-migration-handlers';
import { registerPerformanceProfilerHandlers, setupPerformanceProfilerEventForwarding } from './performance-profiler-handlers';
import { registerDocumentationAgentHandlers, setupDocumentationAgentEventForwarding } from './documentation-agent-handlers';
import { registerDecisionLoggerHandlers } from './decision-logger-handlers';
import { registerPairProgrammingHandlers } from './pair-programming-handlers';
import { registerPipelineGeneratorHandlers, setupPipelineGeneratorEventForwarding } from './pipeline-generator-handlers';
import { registerTeamSyncHandlers } from './team-sync-handlers';
import { registerPluginMarketplaceHandlers } from './plugin-marketplace-handlers';
import { registerArenaHandlers } from './arena-handlers';
import { registerMemoryLifecycleHandlers, setupMemoryLifecycleEventForwarding } from './memory-lifecycle-handlers';
import { registerCICDTriggersHandlers, setupCICDTriggersEventForwarding } from './cicd-triggers-handlers';
import { registerCrossLanguageTranslationHandlers } from './cross-language-translation-handlers';
import { registerSpecApprovalHandlers } from './spec-approval-handlers';
import { registerApiExplorerHandlers } from './api-explorer-handlers';
import { setupTestGenerationHandlers } from './test-generation-handlers';
import { registerCostHandlers } from './cost-handlers';
import { registerVisualProgrammingHandlers, setupVisualProgrammingEventForwarding } from './visual-programming-handlers';

// Re-export all handler registration functions using export...from syntax
export { registerProjectHandlers } from './project-handlers';
export { registerTaskHandlers } from './task-handlers';
export { registerTerminalHandlers } from './terminal-handlers';
export { registerAgenteventsHandlers } from './agent-events-handlers';
export { registerSettingsHandlers } from './settings-handlers';
export { registerFileHandlers } from './file-handlers';
export { registerRoadmapHandlers } from './roadmap-handlers';
export { registerContextHandlers } from './context-handlers';
export { registerEnvHandlers } from './env-handlers';
export { registerLinearHandlers } from './linear-handlers';
export { registerAzureDevOpsHandlers } from './azure-devops-handlers';
export { registerPRDetailsHandlers } from './pr-details-handlers';
export { registerJiraHandlers } from './jira-handlers';
export { registerGithubHandlers } from './github-handlers';
export { registerGitlabHandlers } from './gitlab-handlers';
export { registerIdeationHandlers } from './ideation-handlers';
export { registerChangelogHandlers } from './changelog-handlers';
export { registerInsightsHandlers } from './insights-handlers';
export { registerMemoryHandlers } from './memory-handlers';
export { registerAppUpdateHandlers } from './app-update-handlers';
export { registerDebugHandlers } from './debug-handlers';
export { registerClaudeCodeHandlers } from './claude-code-handlers';
export { registerCopilotCliHandlers } from './copilot-cli-handlers';
export { registerCopilotOAuthHandlers } from './copilot-oauth-handlers';
export { registerMcpHandlers } from './mcp-handlers';
export { registerProfileHandlers } from './profile-handlers';
export { registerScreenshotHandlers } from './screenshot-handlers';
export { registerTerminalWorktreeIpcHandlers } from './terminal';
export { setupQualityHandlers } from './quality-handlers';
export { registerPromptOptimizerHandlers } from './prompt-optimizer-handlers';
export { registerCredentialHandlers } from './credential-handlers';
export { registerGitHubCopilotHandlers } from './github-copilot-handlers';
export { setupNaturalLanguageGitHandlers } from './natural-language-git-handlers';
export { setupSmartEstimationHandlers } from './smart-estimation-handlers';
export { setupConflictPredictorHandlers } from './conflict-predictor-handlers';
export { registerVoiceControlHandlers } from './voice-control-handlers';
export { registerAppEmulatorHandlers } from './app-emulator-handlers';
export { registerLearningLoopHandlers } from './learning-loop-handlers';
export { registerMcpMarketplaceHandlers } from './mcp-marketplace-handlers';
export { registerMultiRepoHandlers } from './multi-repo-handlers';
export { registerSelfHealingHandlers } from './self-healing-handlers';
export { registerBrowserAgentHandlers } from './browser-agent-handlers';
export { registerArchitectureVisualizerHandlers, setupArchitectureVisualizerEventForwarding } from './architecture-visualizer-handlers';
export { registerCodeMigrationHandlers, setupCodeMigrationEventForwarding } from './code-migration-handlers';
export { registerPerformanceProfilerHandlers, setupPerformanceProfilerEventForwarding } from './performance-profiler-handlers';
export { registerDocumentationAgentHandlers, setupDocumentationAgentEventForwarding } from './documentation-agent-handlers';
export { registerDecisionLoggerHandlers } from './decision-logger-handlers';
export { registerPairProgrammingHandlers } from './pair-programming-handlers';
export { registerPipelineGeneratorHandlers, setupPipelineGeneratorEventForwarding } from './pipeline-generator-handlers';
export { registerTeamSyncHandlers } from './team-sync-handlers';
export { registerPluginMarketplaceHandlers } from './plugin-marketplace-handlers';
export { registerArenaHandlers } from './arena-handlers';
export { registerMemoryLifecycleHandlers, setupMemoryLifecycleEventForwarding } from './memory-lifecycle-handlers';
export { registerCICDTriggersHandlers, setupCICDTriggersEventForwarding } from './cicd-triggers-handlers';
export { registerCrossLanguageTranslationHandlers } from './cross-language-translation-handlers';
export { registerSpecApprovalHandlers } from './spec-approval-handlers';
export { registerApiExplorerHandlers } from './api-explorer-handlers';
export { setupTestGenerationHandlers } from './test-generation-handlers';
export { registerCostHandlers } from './cost-handlers';
export { registerVisualProgrammingHandlers, setupVisualProgrammingEventForwarding } from './visual-programming-handlers';

/**
 * Setup all IPC handlers across all domains
 *
 * @param agentManager - The agent manager instance
 * @param terminalManager - The terminal manager instance
 * @param getMainWindow - Function to get the main BrowserWindow
 * @param pythonEnvManager - The Python environment manager instance
 */
export function setupIpcHandlers(
  agentManager: AgentManager,
  terminalManager: TerminalManager,
  getMainWindow: () => BrowserWindow | null,
  pythonEnvManager: PythonEnvManager
): void {
  // Initialize notification service
  notificationService.initialize(getMainWindow);

  // Project handlers (including Python environment setup)
  registerProjectHandlers(pythonEnvManager, agentManager, getMainWindow);

  // Task handlers
  registerTaskHandlers(agentManager, pythonEnvManager, getMainWindow);

  // Terminal and Claude profile handlers
  registerTerminalHandlers(terminalManager, getMainWindow);

  // Terminal worktree handlers (isolated development in worktrees)
  registerTerminalWorktreeIpcHandlers();

  // Agent event handlers (event forwarding from agent manager to renderer)
  registerAgenteventsHandlers(agentManager, getMainWindow);

  // Settings and dialog handlers
  registerSettingsHandlers(agentManager, getMainWindow);

  // File explorer handlers
  registerFileHandlers();

  // Roadmap handlers
  registerRoadmapHandlers(agentManager, getMainWindow);

  // Context and memory handlers
  registerContextHandlers(getMainWindow);

  // Environment configuration handlers
  registerEnvHandlers(getMainWindow);

  // Linear integration handlers
  registerLinearHandlers(agentManager, getMainWindow);

  // Azure DevOps integration handlers
  registerAzureDevOpsHandlers(agentManager, getMainWindow);

  // Universal PR Details handler (supports both GitHub and Azure DevOps)
  registerPRDetailsHandlers();

  // Jira integration handlers
  registerJiraHandlers(agentManager, getMainWindow);

  // GitHub integration handlers
  registerGithubHandlers(agentManager, getMainWindow);

  // GitLab integration handlers
  registerGitlabHandlers(agentManager, getMainWindow);

  // Ideation handlers
  registerIdeationHandlers(agentManager, getMainWindow);

  // Changelog handlers
  registerChangelogHandlers(getMainWindow);

  // Insights handlers
  registerInsightsHandlers(getMainWindow);

  // Memory & infrastructure handlers (for Graphiti/LadybugDB)
  registerMemoryHandlers();

  // App auto-update handlers
  registerAppUpdateHandlers();

  // Debug handlers (logs, debug info, etc.)
  registerDebugHandlers();

  // Claude Code CLI handlers (version checking, installation)
  registerClaudeCodeHandlers();

  // Copilot CLI handlers (version checking, installation, auth)
  registerCopilotCliHandlers();

  // Copilot OAuth handlers (web-based authentication)
  registerCopilotOAuthHandlers();

  // MCP server health check handlers
  registerMcpHandlers();

  // API Profile handlers (custom Anthropic-compatible endpoints)
  registerProfileHandlers();

  // Screenshot capture handlers
  registerScreenshotHandlers();

  // Quality Scorer handlers (AI Code Review)
  setupQualityHandlers();

  // Prompt Optimizer handlers
  registerPromptOptimizerHandlers(getMainWindow);

  // Credential Manager handlers (centralized auth and usage management)
  registerCredentialHandlers();

  // GitHub Copilot CLI handlers (CLI-based authentication)
  registerGitHubCopilotHandlers();

  // Natural Language Git handlers
  setupNaturalLanguageGitHandlers();

  // Smart Estimation handlers
  setupSmartEstimationHandlers();

  // Conflict Predictor handlers
  setupConflictPredictorHandlers();

  // Voice Control handlers
  registerVoiceControlHandlers();
  setupVoiceControlEvents();

  // App Emulator handlers
  registerAppEmulatorHandlers(getMainWindow);

  // Learning Loop handlers (Autonomous Agent Learning Loop)
  registerLearningLoopHandlers(getMainWindow);

  // MCP Marketplace handlers (catalog, install, builder)
  registerMcpMarketplaceHandlers();

  // Multi-Repo Orchestration handlers
  registerMultiRepoHandlers(agentManager, getMainWindow);

  // Self-Healing Codebase + Incident Responder handlers
  registerSelfHealingHandlers(getMainWindow);

  // Browser Agent handlers (built-in browser for testing and visual validation)
  registerBrowserAgentHandlers(getMainWindow);

  // Architecture Visualizer handlers
  registerArchitectureVisualizerHandlers();
  setupArchitectureVisualizerEventForwarding();

  // Code Migration Agent handlers
  registerCodeMigrationHandlers();
  setupCodeMigrationEventForwarding();

  // Performance Profiler Agent handlers
  registerPerformanceProfilerHandlers();
  setupPerformanceProfilerEventForwarding();

  // Documentation Agent handlers
  registerDocumentationAgentHandlers();
  setupDocumentationAgentEventForwarding();

  // Agent Decision Logger handlers (Feature 30)
  registerDecisionLoggerHandlers();

  // AI Pair Programming handlers (Feature 10)
  registerPairProgrammingHandlers(getMainWindow);

  // Pipeline Generator handlers (Feature 23)
  registerPipelineGeneratorHandlers();
  setupPipelineGeneratorEventForwarding(getMainWindow);

  // Team Knowledge Sync handlers (Feature 31)
  registerTeamSyncHandlers();

  // Plugin Marketplace handlers (Feature 37)
  registerPluginMarketplaceHandlers();

  // Arena Mode handlers (Feature 9) — Blind A/B model comparison
  registerArenaHandlers(getMainWindow);

  // Memory Lifecycle Manager handlers (Feature 43)
  registerMemoryLifecycleHandlers();
  setupMemoryLifecycleEventForwarding(getMainWindow);

  // CI/CD Deployment Triggers handlers (Feature 44)
  registerCICDTriggersHandlers();
  setupCICDTriggersEventForwarding(getMainWindow);

  // Cross-Language Translation Agent handlers (Feature 41)
  registerCrossLanguageTranslationHandlers();

  // Spec Approval Workflow handlers (Feature 42)
  registerSpecApprovalHandlers();

  // API Explorer — project route scanning
  registerApiExplorerHandlers();

  // Test Generation handlers
  setupTestGenerationHandlers(getMainWindow);

  // Cost Estimator handlers
  registerCostHandlers();

  // Visual Programming handlers (diagram → code, code → diagram)
  registerVisualProgrammingHandlers(getMainWindow);
  setupVisualProgrammingEventForwarding(getMainWindow);

  console.warn('[IPC] All handler modules registered successfully');
}
