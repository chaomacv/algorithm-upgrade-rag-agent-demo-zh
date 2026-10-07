import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Protocol


class ChatProvider(Protocol):
    def complete(self, messages: List[Dict[str, str]], response_format: Optional[Dict[str, str]] = None) -> str:
        """Return one assistant message for a chat-style request."""
        ...


class OpenAICompatibleChatProvider:
    """Chat provider for DeepSeek, OpenAI-compatible gateways, and similar APIs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-flash",
        api_key_env: str = "DEEPSEEK_API_KEY",
        timeout: int = 60,
        verify_ssl: bool = True,
    ) -> None:
        """Store provider settings from config, arguments, or environment."""
        self.api_key = api_key or os.environ.get(api_key_env)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        if not self.api_key:
            raise ValueError(f"{api_key_env} is required for LLM calls.")

    def complete(self, messages: List[Dict[str, str]], response_format: Optional[Dict[str, str]] = None) -> str:
        """Call an OpenAI-compatible chat completions endpoint."""
        body: Dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if response_format:
            body["response_format"] = response_format
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            context = None if self.verify_ssl else ssl._create_unverified_context()
            with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed: HTTP {exc.code}: {detail}") from exc
        return payload["choices"][0]["message"]["content"]


def build_chat_provider(config: Dict[str, object]) -> ChatProvider:
    """Create a chat provider from a config dictionary."""
    provider = str(config.get("provider", "openai-compatible"))
    if provider not in {"deepseek", "openai-compatible"}:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    return OpenAICompatibleChatProvider(
        api_key=config.get("api_key") if isinstance(config.get("api_key"), str) else None,
        base_url=str(config.get("base_url", "https://api.deepseek.com")),
        model=str(config.get("model", "deepseek-flash")),
        api_key_env=str(config.get("api_key_env", "DEEPSEEK_API_KEY")),
        timeout=int(config.get("timeout", 60)),
        verify_ssl=bool(config.get("verify_ssl", True)),
    )
