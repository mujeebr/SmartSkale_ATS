"""Abstract interfaces for large language model clients."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Minimal protocol required from any LLM integration."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the model's text response for a given prompt."""
