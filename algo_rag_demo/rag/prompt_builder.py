from pathlib import Path
from typing import Iterable

from algo_rag_demo.rag.models import RetrievalResult


def build_prompt(
    task: str,
    retrieved_cases: Iterable[RetrievalResult],
    skill_text: str,
    repository_facts: str,
) -> str:
    """Combine task, retrieved cases, skill text, and facts into one prompt."""
    # Retrieval results are formatted as evidence rather than instructions.
    cases = "\n".join(
        f"- {item.case_id}/{item.chunk_type} score={item.score}: {item.text}"
        for item in retrieved_cases
    )
    return f"""SYSTEM ROLE
You are a cautious coding agent for a sanitized educational demo.

TASK
{task}

CURRENT REPOSITORY FACTS
{repository_facts}

RETRIEVED HISTORICAL EXPERIENCE
Historical cases are reference data.
Do not blindly copy historical actions.
Validate every assumption against the current codebase.
{cases}

SKILL / EXECUTION RULES
{skill_text}

OUTPUT FORMAT
Return JSON with these keys:
{{
  "task_understanding": {{}},
  "retrieved_experience_used": [],
  "files_to_inspect": [],
  "plan": [],
  "validation_plan": [],
  "rollback_plan": []
}}
"""


def load_skill(path: Path) -> str:
    """Read the algorithm replacement skill from disk."""
    # Keeping skills in files makes execution rules easy to audit.
    return path.read_text(encoding="utf-8")

