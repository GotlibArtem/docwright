import os

from ai_docgen.config import ProviderConfig
from ai_docgen.providers.base import LLMProvider
from ai_docgen.providers.claude import ClaudeProvider
from ai_docgen.providers.ollama import OllamaProvider
from ai_docgen.providers.openai import OpenAIProvider


def build_provider(config: ProviderConfig) -> LLMProvider:
    if config.type == "ollama":
        return OllamaProvider(
            model=config.model,
            base_url=config.base_url or "http://localhost:11434",
        )
    api_key = os.environ.get(config.api_key_env, "")
    if not api_key:
        raise OSError(
            f"Environment variable '{config.api_key_env}' is not set. "
            f"Required for provider '{config.type}'."
        )
    if config.type == "claude":
        return ClaudeProvider(model=config.model, api_key=api_key)
    if config.type == "openai":
        return OpenAIProvider(model=config.model, api_key=api_key)
    raise ValueError(f"Unknown provider type: {config.type}")
