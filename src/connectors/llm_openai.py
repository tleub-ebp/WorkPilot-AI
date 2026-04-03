from typing import Any

from .llm_base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    def connect(self) -> None:
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")
        self._client = openai
        self._client.api_key = self.api_key
        self._client.base_url = self.base_url

    def validate(self) -> bool:
        try:
            self.connect()
            models = self._client.Model.list()
            return any(m.id == self.model for m in models.data)
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        self.connect()
        try:
            response = self._client.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            return response.choices[0].message["content"]
        except Exception:
            raise

    def get_capabilities(self) -> dict[str, Any]:
        return {"models": [self.model], "provider": "openai"}

    def get_config_schema(self) -> dict[str, Any]:
        return {"api_key": "str", "model": "str", "base_url": "str (optional)"}

    @classmethod
    def get_name(cls) -> str:
        return "openai"
