"""Azure DevOps Connector - Root package."""

try:
    from . import config
    __all__ = ["config"]
except ImportError:
    # python-dotenv may not be installed in all environments.
    # Allow subpackages like src.connectors to be imported independently.
    __all__ = []
