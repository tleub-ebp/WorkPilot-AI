// Note: ProjectSettings component is deprecated - use unified AppSettings instead

export { AgentConfigSection } from "./AgentConfigSection";
// New refactored components for ProjectSettings dialog
export { AutoBuildIntegration } from "./AutoBuildIntegration";
export { ClaudeAuthSection } from "./ClaudeAuthSection";
// Utility components
export { CollapsibleSection } from "./CollapsibleSection";
export { ConnectionStatus } from "./ConnectionStatus";
export { GeneralSettings } from "./GeneralSettings";
export { GitHubIntegrationSection } from "./GitHubIntegrationSection";
export type { UseProjectSettingsReturn } from "./hooks/useProjectSettings";
export { useProjectSettings } from "./hooks/useProjectSettings";
export { InfrastructureStatus } from "./InfrastructureStatus";
export { IntegrationSettings } from "./IntegrationSettings";
export { LinearIntegrationSection } from "./LinearIntegrationSection";
export { MemoryBackendSection } from "./MemoryBackendSection";
export { MemoryLifecycleSection } from "./MemoryLifecycleSection";
export { NotificationsSection } from "./NotificationsSection";
export { PasswordInput } from "./PasswordInput";
export { SecuritySettings } from "./SecuritySettings";
export { StatusBadge } from "./StatusBadge";
