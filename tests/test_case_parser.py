from pathlib import Path

import json

from algo_rag_demo.case_pipeline.parser import LLMCaseExtractor, RuleBasedCaseExtractor
from algo_rag_demo.case_pipeline.schema import Conversation
from algo_rag_demo.config import RAW_DIR
from algo_rag_demo.utils.jsonio import read_json


def test_raw_conversation_to_case():
    """Verify the rule extractor creates the canonical DRE case."""
    # This test keeps the offline extraction path stable.
    conversation = Conversation(**read_json(RAW_DIR / "conversation_dre_upgrade.json"))
    case = RuleBasedCaseExtractor().extract(conversation)
    assert case.case_id == "CASE_DRE_001"
    assert case.module == "DRE"
    assert case.validation["algorithm_switch"] == "passed"


class FakeProvider:
    def complete(self, messages):
        """Return a deterministic LLM-style JSON response for tests."""
        # The fake provider avoids network calls in unit tests.
        return json.dumps(
            {
                "case_id": "CASE_FAKE_001",
                "module": "DRE",
                "task": "Replace a demo algorithm",
                "old_algorithm": "OldDemo",
                "new_algorithm": "NewDemo",
                "constraints": {"interface": ["Keep output schema stable"]},
                "steps": ["Inspect interface", "Patch adapter", "Run validation"],
                "problems": [
                    {
                        "stage": "interface validation",
                        "symptom": "missing field",
                        "root_cause": "new output omitted required field",
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
    # This covers the provider-neutral path without calling DeepSeek.
    conversation = Conversation(
        conversation_id="CONV_FAKE_001",
        task="Fake task",
        messages=[],
    )
    case = LLMCaseExtractor(FakeProvider()).extract(conversation)
    assert case.case_id == "CASE_FAKE_001"
    assert case.constraints["interface"] == ["Keep output schema stable"]

