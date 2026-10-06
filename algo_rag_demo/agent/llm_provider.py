from typing import Protocol


class LLMProvider(Protocol):
    def complete(self, prompt: str) -> str:
        """Return one completion for a prompt string."""
        ...

