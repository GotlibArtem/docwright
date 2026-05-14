import httpx

from docwright.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def complete(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            return str(response.json()["message"]["content"])
