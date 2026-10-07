import json

from algo_rag_demo.agent.planner import LLMPlanner
from algo_rag_demo.rag.models import RetrievalResult


class FakeProvider:
    """Minimal chat provider used to test LLMPlanner without a network call."""

    def complete(self, messages, response_format=None):
        """Return a valid planner JSON object."""
        assert response_format == {"type": "json_object"}
        assert messages[0]["role"] == "system"
        assert "RETRIEVED_EVIDENCE" in messages[1]["content"]
        return json.dumps(
            {
                "task_understanding": {"target_module": "Ranking"},
                "retrieved_experience_used": ["CASE_CUSTOM_001:solution"],
                "files_to_inspect": ["ranking/pipeline.py"],
                "plan": ["Patch compatibility adapter for metadata"],
                "validation_plan": ["Run interface tests"],
                "rollback_plan": ["Restore checkpoint"],
                "risks": ["metadata schema drift"],
            }
        )


def test_llm_planner_parses_provider_json():
    """Verify the LLM planner consumes provider JSON and returns plan fields."""
    result = RetrievalResult(
        score=0.9,
        case_id="CASE_CUSTOM_001",
        chunk_id="CASE_CUSTOM_001:solution",
        chunk_type="solution",
        text="Add adapter compatibility for metadata.",
        module="Ranking",
        final_status="success",
        source="CONV_CUSTOM_001",
    )

    plan = LLMPlanner(FakeProvider()).plan("Replace legacy ranker", [result], "ranking module exists")

    assert plan["task_understanding"]["target_module"] == "Ranking"
    assert plan["plan"] == ["Patch compatibility adapter for metadata"]
    assert plan["rollback_plan"] == ["Restore checkpoint"]
