"""
Runtime Factory: Choix du runtime agent selon ProviderConfig
"""
from core.provider_config import ProviderConfig
from core.runtimes.litellm_runtime import LiteLLMRuntime
from core.runtimes.copilot_runtime import CopilotRuntime
from core.runtimes.claude_sdk_runtime import ClaudeSDKRuntime  # à décommenter si le fichier existe


def create_agent_runtime(spec_dir, phase, project_dir, agent_type, cli_provider=None, cli_model=None, cli_thinking=None, config=None):
    """
    Factory pour choisir le runtime agent selon ProviderConfig.
    Utilise CopilotRuntime si provider = 'copilot',
    ClaudeSDKRuntime si provider = 'anthropic-sdk', sinon LiteLLMRuntime.
    """
    if config is None:
        config = ProviderConfig.load_provider_config(phase, spec_dir, cli_provider, cli_model)

    # Copilot CLI runtime
    if cli_provider == 'copilot' or (hasattr(config, 'provider') and config.provider == 'copilot'):
        return CopilotRuntime(spec_dir, phase, project_dir, agent_type, config, cli_thinking)

    if hasattr(config, 'is_claude_sdk') and config.is_claude_sdk:
        # return ClaudeSDKRuntime(spec_dir, phase, project_dir, agent_type, config, cli_thinking)
        raise NotImplementedError("ClaudeSDKRuntime non disponible dans ce workspace.")
    else:
        return LiteLLMRuntime(spec_dir, phase, project_dir, agent_type, config, cli_thinking)
