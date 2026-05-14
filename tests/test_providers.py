from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock

from ai_docgen.config import ProviderConfig
from ai_docgen.providers.base import LLMProvider
from ai_docgen.providers.claude import ClaudeProvider
from ai_docgen.providers.factory import build_provider
from ai_docgen.providers.ollama import OllamaProvider


def test_provider_is_abstract() -> None:
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_claude_provider_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [TextBlock(type="text", text="Updated README content")]
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("ai_docgen.providers.claude.AsyncAnthropic", return_value=mock_client):
        provider = ClaudeProvider(model="claude-sonnet-4-6", api_key="test-key")
        result = await provider.complete(system="You are a docs writer.", user="Update this.")
        assert result == "Updated README content"


@pytest.mark.asyncio
async def test_ollama_provider_complete() -> None:
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"message": {"content": "Ollama response"}})
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = OllamaProvider(model="llama3", base_url="http://localhost:11434")
        result = await provider.complete(system="sys", user="user msg")
        assert result == "Ollama response"


def test_build_provider_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    cfg = ProviderConfig(type="claude", model="claude-sonnet-4-6", api_key_env="ANTHROPIC_API_KEY")
    provider = build_provider(cfg)
    assert isinstance(provider, ClaudeProvider)


def test_build_provider_ollama() -> None:
    cfg = ProviderConfig(
        type="ollama", model="llama3", api_key_env="", base_url="http://localhost:11434"
    )
    provider = build_provider(cfg)
    assert isinstance(provider, OllamaProvider)


def test_build_provider_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = ProviderConfig(type="claude", model="claude-sonnet-4-6", api_key_env="ANTHROPIC_API_KEY")
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        build_provider(cfg)
