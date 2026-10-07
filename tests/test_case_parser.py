import json

from algo_rag_demo.case_pipeline.parser import LLMCaseExtractor
from algo_rag_demo.case_pipeline.schema import Conversation


class FakeProvider:
    def complete(self, messages, response_format=None):
        """Return a deterministic LLM-style JSON response for tests."""
        assert response_format == {"type": "json_object"}
        return json.dumps(
            {
                "case_id": "CASE_FAKE_001",
                "module": "Ranking",
                "task": "Replace a ranking algorithm",
                "old_algorithm": "OldRanker",
                "new_algorithm": "NewScorer",
                "constraints": {"interface": ["Keep output schema stable"]},
                "steps": ["Inspect interface", "Patch adapter", "Run validation"],
                "problems": [
                    {
                        "stage": "interface validation",
                        "symptom": "missing field",
                        "root_cause": "new output omitted required metadata",
                    }
                ],
                "solutions": [{"problem": "missing field", "solution": "add adapter compatibility"}],
                "validation": {"interface": "passed"},
                "final_status": "success",
                "reusable_experience": ["Validate interface before declaring success"],
                "source_conversation_id": "CONV_FAKE_001",
            }
        )


def test_llm_case_extractor_uses_provider_json():
    """Verify LLMCaseExtractor parses provider JSON into a case model."""
    conversation = Conversation(
        conversation_id="CONV_FAKE_001",
        task="Fake task",
        messages=[],
    )
    case = LLMCaseExtractor(FakeProvider()).extract(conversation)
    assert case.case_id == "CASE_FAKE_001"
    assert case.module == "Ranking"
    assert case.constraints["interface"] == ["Keep output schema stable"]
