from openai import AsyncOpenAI

from docwright.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(self, system: str, user: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return content or ""
