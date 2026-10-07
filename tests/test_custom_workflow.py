from pathlib import Path
from tempfile import TemporaryDirectory

from algo_rag_demo.agent.planner import LLMPlanner
from algo_rag_demo.rag.index_builder import build_index_from_cases
from algo_rag_demo.rag.retriever import Retriever


def test_custom_case_builds_index_and_plan():
    """Verify custom cases can build a run-local index and produce a generic plan."""
    # This test guards the public "bring your own case data" entrypoint.
    case_dir = Path("examples/custom_data/cases")
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        knowledge_dir = root / "knowledge"
        index_dir = root / "index"

        cases, chunks, dimension = build_index_from_cases(
            provider_name="mock",
            case_dir=case_dir,
            knowledge_dir=knowledge_dir,
            index_dir=index_dir,
        )
        assert cases == 1
        assert chunks == 3
        assert dimension == 64
        assert (knowledge_dir / "chunks.json").exists()
        assert (index_dir / "metadata.json").exists()

        task = Path("examples/custom_data/task.txt").read_text(encoding="utf-8")
        results = Retriever(index_dir=index_dir, provider_name="mock", case_dir=case_dir).search(task, top_k=1)
        assert results[0].case_id == "CASE_CUSTOM_001"

        class TestProvider:
            def complete(self, messages, response_format=None):
                """Return test planning fields without a network dependency."""
                return '{"plan": ["Inspect metadata"], "validation_plan": ["Check interface"]}'
        plan = LLMPlanner(TestProvider()).plan(task, results)
        assert plan["plan"] == ["Inspect metadata"]
        assert "validation_plan" in plan
