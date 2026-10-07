import json
import re
from pathlib import Path
from typing import Dict, Optional

from algo_rag_demo.agent.llm_provider import ChatProvider
from algo_rag_demo.case_pipeline.schema import Conversation, EngineeringCase, model_to_dict
from algo_rag_demo.utils.jsonio import read_json, write_json


class LLMCaseExtractor:
    """Extract a reusable EngineeringCase from a historical conversation."""

    system_prompt = """You extract reusable engineering experience from historical conversations.
Return exactly one JSON object matching this schema:
{
  "case_id": "CASE_*",
  "module": "short module or component name",
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
Keep only reusable, sanitized engineering knowledge. Do not include secrets, private paths, customer data, or raw internal logs."""

    def __init__(self, provider: ChatProvider) -> None:
        """Store the LLM provider used for schema-driven extraction."""
        self.provider = provider

    def extract(self, conversation: Conversation) -> EngineeringCase:
        """Ask the LLM to turn one conversation into an EngineeringCase."""
        user_prompt = (
            "Extract a structured EngineeringCase from this conversation JSON. "
            "Focus on reusable task, constraints, solution, validation, and lessons.\n\n"
            + json.dumps(model_to_dict(conversation), indent=2, ensure_ascii=False)
        )
        content = self.provider.complete(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        data = _parse_json_object(content)
        data.setdefault("source_conversation_id", conversation.conversation_id)
        return EngineeringCase(**data)


def extract_case_file(raw_path: Path, output_path: Path, extractor: LLMCaseExtractor) -> EngineeringCase:
    """Extract one raw conversation file and write the resulting case JSON."""
    conversation = Conversation(**read_json(raw_path))
    case = extractor.extract(conversation)
    write_json(output_path, case)
    return case


def load_case_file(case_path: Path) -> EngineeringCase:
    """Load one already structured EngineeringCase JSON file."""
    return EngineeringCase(**read_json(case_path))


def _parse_json_object(content: str) -> Dict[str, object]:
    """Parse the first JSON object returned by an LLM response."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))
