import json
import os
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Protocol

from algo_rag_demo.case_pipeline.schema import Conversation, EngineeringCase, model_to_dict
from algo_rag_demo.utils.jsonio import read_json, write_json


class RuleBasedCaseExtractor:
    """Extracts a stable teaching case from the synthetic DRE conversation."""

    def extract(self, conversation: Conversation) -> EngineeringCase:
        """Extract the fixed DRE teaching case from a known demo conversation."""
        # This fallback keeps CI deterministic when no LLM provider is available.
        text = "\n".join(message.content for message in conversation.messages).lower()
        if "residual_map" not in text or "newllf" not in text:
            raise ValueError("Conversation does not look like the DRE upgrade demo.")

        return EngineeringCase(
            case_id="CASE_DRE_001",
            module="DRE",
            task="Replace OldDRE with NewLLF",
            old_algorithm="OldDRE",
            new_algorithm="NewLLF",
            constraints={
                "interface": [
                    "Keep downstream public interface unchanged",
                    "Preserve residual_map compatibility",
                ],
                "engineering": [
                    "Do not modify unrelated modules",
                    "Keep rollback capability",
                ],
            },
            steps=[
                "Locate DRE entry point",
                "Compare OldDRE and NewLLF outputs",
                "Add compatibility adapter",
                "Switch pipeline configuration",
                "Run interface, build, runtime, algorithm switch, and rollback validation",
            ],
            problems=[
                {
                    "stage": "first replacement",
                    "symptom": "KeyError: residual_map",
                    "root_cause": "NewLLF output does not contain residual_map",
                },
                {
                    "stage": "runtime validation",
                    "symptom": "OldDRE still appears in runtime log",
                    "root_cause": "Pipeline configuration was not switched",
                },
            ],
            solutions=[
                {
                    "problem": "missing residual_map",
                    "solution": "Add compatibility logic in demo_project/src/modules/dre_adapter.py",
                },
                {
                    "problem": "old algorithm still active",
                    "solution": "Update demo_project/config/pipeline.json to new_llf",
                },
            ],
            validation={
                "interface": "passed",
                "build": "passed",
                "runtime": "passed",
                "algorithm_switch": "passed",
                "rollback": "passed",
            },
            final_status="success",
            reusable_experience=[
                "Do not directly replace an algorithm before checking downstream interface dependencies",
                "Compilation success does not prove the new algorithm is active",
                "Algorithm switch must be verified using runtime evidence",
                "When execution fails, retrieve historical cases again using the concrete error",
            ],
            source_conversation_id=conversation.conversation_id,
        )


class LLMCaseExtractor:
    """Provider-neutral LLM extractor that returns an EngineeringCase."""

    system_prompt = """You extract sanitized engineering knowledge from engineer-agent conversations.
Return exactly one JSON object matching this schema:
{
  "case_id": "CASE_*",
  "module": "short module name",
  "task": "short task summary",
  "old_algorithm": "string or null",
  "new_algorithm": "string or null",
  "constraints": {"category": ["constraint"]},
  "steps": ["step"],
  "problems": [{"stage": "stage", "symptom": "symptom", "root_cause": "root cause"}],
  "solutions": [{"problem": "problem", "solution": "solution"}],
  "validation": {"check": "passed|failed|not_run"},
  "final_status": "success|failed|partial",
  "reusable_experience": ["lesson"],
  "source_conversation_id": "conversation id"
}
Use only synthetic/public-safe information from the conversation. Do not invent private paths, company internals, secrets, model weights, customer data, or real internal logs."""

    def __init__(self, provider: "ChatProvider") -> None:
        """Store the chat provider used for schema-driven extraction."""
        self.provider = provider

    def extract(self, conversation: Conversation) -> EngineeringCase:
        """Ask the provider to turn one conversation into an EngineeringCase."""
        # The model sees structured JSON so it can preserve source identifiers.
        user_prompt = (
            "Extract a structured EngineeringCase from this conversation JSON. "
            "Prefer stable reusable engineering knowledge over transcript noise.\n\n"
            + json.dumps(model_to_dict(conversation), indent=2, ensure_ascii=False)
        )
        content = self.provider.complete(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        data = _parse_json_object(content)
        data.setdefault("source_conversation_id", conversation.conversation_id)
        return EngineeringCase(**data)


class ChatProvider(Protocol):
    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Return one assistant message for a chat-style request."""
        ...


class DeepSeekChatProvider:
    """OpenAI-compatible DeepSeek chat provider using the standard library."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        verify_ssl: Optional[bool] = None,
    ) -> None:
        """Read DeepSeek connection settings from arguments or environment."""
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"
        self.timeout = timeout
        env_verify = os.environ.get("DEEPSEEK_VERIFY_SSL", "true").lower()
        self.verify_ssl = verify_ssl if verify_ssl is not None else env_verify not in {"0", "false", "no"}
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeek extraction.")

    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Call DeepSeek's OpenAI-compatible chat completions endpoint."""
        # The response_format hint asks DeepSeek to return strict JSON content.
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
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
            raise RuntimeError(f"DeepSeek request failed: HTTP {exc.code}: {detail}") from exc
        return payload["choices"][0]["message"]["content"]


def _parse_json_object(content: str) -> Dict[str, object]:
    """Parse the first JSON object returned by an LLM response."""
    # Some models wrap JSON in prose, so fall back to extracting the object span.
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def extract_case_file(raw_path: Path, output_path: Path, extractor: Optional[object] = None) -> EngineeringCase:
    """Extract one raw conversation file and write the resulting case JSON."""
    # The caller can inject either the rule-based extractor or an LLM extractor.
    conversation = Conversation(**read_json(raw_path))
    active_extractor = extractor or RuleBasedCaseExtractor()
    case = active_extractor.extract(conversation)
    write_json(output_path, case)
    return case

