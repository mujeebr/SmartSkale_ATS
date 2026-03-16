"""Concrete `LLMClient` implementation that talks to OpenAI chat completions."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

from ...core.llm.base import LLMClient


class OpenAIChatCompletionsClient(LLMClient):
    """LLM client that wraps the OpenAI chat completions API."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        """Load configuration and construct the underlying OpenAI client."""
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to .env or export it in your environment."
            )

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        """Send a prompt to the configured OpenAI model and return the text content."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
