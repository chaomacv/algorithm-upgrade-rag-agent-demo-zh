import json
from pathlib import Path
from tempfile import TemporaryDirectory

from algo_rag_demo.agent.executor import FileProjectAdapter, build_project_adapter
from algo_rag_demo.agent.planner import LLMPlanner
from algo_rag_demo.agent.workflow import run_agent
from algo_rag_demo.rag.index_builder import build_index_from_cases
from algo_rag_demo.rag.retriever import Retriever
from algo_rag_demo.utils.jsonio import read_json


class RecordingRetriever:
    """Record real index queries so tests can prove failure triggers retrieval."""

    def __init__(self, root):
        """Build a small test index from the bundled Case."""
        build_index_from_cases("mock", case_dir=Path("examples/custom_data/cases"),
                               knowledge_dir=root / "knowledge", index_dir=root / "index")
        self.retriever = Retriever(index_dir=root / "index", provider_name="mock")
        self.queries = []

    def search(self, query, **kwargs):
        """Record the query and delegate to the actual vector retriever."""
        self.queries.append(query)
        return self.retriever.search(query, **kwargs)


class ScriptedProvider:
    """Return test-only actions while exercising the production LLMPlanner."""

    def __init__(self, original, repair=True, immediate=False):
        """Choose the first action and optional repair action for this test."""
        self.original = original
        self.repair = repair
        self.immediate = immediate
        self.prompts = []

    def complete(self, messages, response_format=None):
        """Provide a direct replacement or compatibility adapter patch."""
        self.prompts.append(messages[-1]["content"])
        actions = [{"tool": "write_file", "path": "config.json",
                    "content": json.dumps({"algorithm": "NeuralScorer"})}]
        if self.immediate or (self.repair and len(self.prompts) > 1):
            content = self.original.replace(
                "rows = neural_scorer(items)",
                'rows = [{"id": row["id"], "score": row["value"], '
                '"metadata": {"confidence": row["confidence"], "reason": row["explanation"]}} '
                'for row in neural_scorer(items)]',
            )
            actions.append({"tool": "write_file", "path": "ranking.py", "content": content})
        return json.dumps({"plan": ["Upgrade ranker"], "actions": actions})


def _components(root, repair=True, immediate=False):
    """Create the configured real file executor and a controlled chat response."""
    config = read_json(Path("configs/deepseek_bge_m3.json"))["execution"]
    adapter = build_project_adapter(config, root)
    original = (adapter.workspace / "ranking.py").read_text(encoding="utf-8")
    provider = ScriptedProvider(original, repair=repair, immediate=immediate)
    return adapter, provider, RecordingRetriever(root)


def test_failure_retrieves_error_and_repairs_actual_code():
    """Prove an actual schema failure feeds a new query and ends in validated success."""
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        adapter, provider, retriever = _components(root)
        report = run_agent("Replace LegacyRanker with NeuralScorer", retriever,
                           LLMPlanner(provider), adapter, root, skill="Preserve downstream metadata.")
        assert report["status"] == "success"
        assert [attempt["passed"] for attempt in report["attempts"]] == [False, True]
        assert len(retriever.queries) == 2
        assert "Validation failure" in retriever.queries[1]
        assert "PREVIOUS VALIDATION" in provider.prompts[1]
        assert "Preserve downstream metadata" in provider.prompts[0]
        assert adapter.validate()["passed"] is True
        assert (root / "attempts/01/error_analysis.json").exists()
        assert not (root / "attempts/02/error_analysis.json").exists()


def test_first_attempt_can_succeed_without_forced_failure():
    """Prove a correct first model response ends immediately."""
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        adapter, provider, retriever = _components(root, immediate=True)
        report = run_agent("Upgrade ranker", retriever, LLMPlanner(provider), adapter, root)
        assert report["status"] == "success"
        assert len(report["attempts"]) == len(provider.prompts) == 1


def test_exhausted_retries_restore_original_files():
    """Verify failed validation restores original bytes instead of reporting success."""
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        adapter, provider, retriever = _components(root, repair=False)
        before = {name: adapter._path(name).read_bytes() for name in adapter.allowed_files}
        report = run_agent("Upgrade ranker", retriever, LLMPlanner(provider), adapter, root, max_attempts=2)
        assert report["status"] == "rolled_back"
        assert report["rollback"]["restored"] is True
        assert all(adapter._path(name).read_bytes() == data for name, data in before.items())
        assert (root / "checkpoint/manifest.json").exists()
        assert len(report["attempts"]) == 2


def test_edit_batch_is_atomic_on_invalid_tool_or_path():
    """Reject attempts to edit validation or escape the workspace before any writes."""
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        adapter, _, _ = _components(root)
        before = (adapter.workspace / "config.json").read_bytes()
        for bad_path in ["validate.py", "../escape.py", str(root / "outside.py")]:
            try:
                adapter.execute({"actions": [
                    {"tool": "write_file", "path": "config.json", "content": "{}"},
                    {"tool": "write_file", "path": bad_path, "content": "bad"},
                ]})
            except ValueError:
                pass
            else:
                raise AssertionError("Expected invalid action to be rejected.")
            assert (adapter.workspace / "config.json").read_bytes() == before
        try:
            adapter.execute({"actions": [{"tool": "shell", "command": "anything"}]})
        except ValueError:
            pass
        else:
            raise AssertionError("Shell actions must be rejected.")


def test_validation_timeout_is_failure():
    """Verify a timed-out check produces failure evidence and permits rollback."""
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        config = read_json(Path("configs/deepseek_bge_m3.json"))["execution"]
        config["validation_commands"] = [["{python}", "-c", "import time; time.sleep(2)"]]
        config["timeout"] = 1
        adapter = FileProjectAdapter(config, root)
        adapter.checkpoint()
        assert adapter.validate()["checks"][0]["error"] == "Validation timed out."
        assert adapter.rollback()["restored"] is True


def test_retrieval_exception_after_mutation_rolls_back():
    """Ensure an infrastructure failure during retry cannot leave changes applied."""
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        adapter, provider, retriever = _components(root, repair=False)
        search = retriever.search
        def failing_search(query, **kwargs):
            """Fail only after the first actual execution and validation."""
            if retriever.queries:
                raise RuntimeError("retrieval unavailable")
            return search(query, **kwargs)
        retriever.search = failing_search
        try:
            run_agent("Upgrade", retriever, LLMPlanner(provider), adapter, root)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected retrieval failure.")
        report = read_json(root / "final_report.json")
        assert report["status"] == "failed"
        assert report["rollback"]["restored"] is True
        assert json.loads((adapter.workspace / "config.json").read_text())["algorithm"] == "LegacyRanker"


def test_failed_restore_is_reported_as_rollback_failed():
    """Verify restoration exceptions are preserved in the final report."""
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        adapter, provider, retriever = _components(root, repair=False)
        def failed_rollback():
            """Simulate a disk error during restoration."""
            raise OSError("restore unavailable")
        adapter.rollback = failed_rollback
        report = run_agent("Upgrade", retriever, LLMPlanner(provider), adapter, root, max_attempts=1)
        assert report["status"] == "rollback_failed"
        assert report["rollback"]["restored"] is False
        assert report["rollback"]["error"] == "restore unavailable"
