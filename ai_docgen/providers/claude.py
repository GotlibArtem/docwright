from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from ai_docgen.providers.base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key)

    async def complete(self, system: str, user: str) -> str:
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        block = message.content[0]
        if not isinstance(block, TextBlock):
            raise ValueError(f"Unexpected content block type: {type(block)}")
        return block.text
