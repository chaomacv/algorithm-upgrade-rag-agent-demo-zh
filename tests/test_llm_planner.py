import json

from algo_rag_demo.agent.planner import LLMPlanner
from algo_rag_demo.rag.models import RetrievalResult


class FakeProvider:
    """Minimal chat provider used to test LLMPlanner without a network call."""

    def complete(self, messages):
        """Return a valid planner JSON object."""
        assert messages[0]["role"] == "system"
        assert "RETRIEVED_EVIDENCE" in messages[1]["content"]
        return json.dumps(
            {
                "task_understanding": {"target_module": "DRE"},
                "retrieved_experience_used": ["CASE_DRE_001:solution"],
                "files_to_inspect": ["demo_project/src/pipeline.py"],
                "plan": ["Patch compatibility adapter"],
                "validation_plan": ["Run interface tests"],
                "rollback_plan": ["Restore checkpoint"],
            }
        )


def test_llm_planner_parses_provider_json():
    """Verify the LLM planner consumes provider JSON and returns plan fields."""
    result = RetrievalResult(
        score=0.9,
        case_id="CASE_DRE_001",
        chunk_id="CASE_DRE_001:solution",
        chunk_type="solution",
        text="Add adapter compatibility for residual_map.",
        module="DRE",
        final_status="success",
        source="examples/data/knowledge/chunks.json",
    )

    plan = LLMPlanner(FakeProvider()).plan("Replace OldDRE with NewLLF", [result])

    assert plan["task_understanding"]["target_module"] == "DRE"
    assert plan["plan"] == ["Patch compatibility adapter"]
    assert plan["rollback_plan"] == ["Restore checkpoint"]
