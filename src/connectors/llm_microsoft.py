from .llm_base import BaseLLMProvider
from typing import Any, Dict

class MicrosoftAzureProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4", endpoint: str = "https://api.openai.azure.com/v1"):
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self._client = None

    def connect(self) -> None:
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is required for Azure OpenAI. Install with: pip install openai")
        self._client = openai
        self._client.api_key = self.api_key
        self._client.api_base = self.endpoint

    def validate(self) -> bool:
        try:
            self.connect()
            models = self._client.Model.list()
            return any(self.model in m.id for m in models.data)
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        self.connect()
        response = self._client.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message["content"]

    def get_capabilities(self) -> Dict[str, Any]:
        return {"models": [self.model], "provider": "microsoft"}

    def get_config_schema(self) -> Dict[str, Any]:
        return {"api_key": "str", "model": "str", "endpoint": "str"}

    @classmethod
    def get_name(cls) -> str:
        return "microsoft"
