import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
from pydantic import ValidationError

from algo_rag_demo import cli
from algo_rag_demo.agent.executor import FileProjectAdapter
from algo_rag_demo.case_pipeline.parser import extract_case_directory
from algo_rag_demo.case_pipeline.schema import EngineeringCase, KnowledgeChunk
from algo_rag_demo.rag.embedding import BgeM3EmbeddingProvider
from algo_rag_demo.rag.index_builder import load_cases, save_index
from algo_rag_demo.rag.retriever import Retriever
from algo_rag_demo.utils.jsonio import parse_json_object, read_json, write_json


def _chunk(case_id, module="Ranking", status="success"):
    """Create minimal retrieval metadata for ranking and filtering tests."""
    return KnowledgeChunk(case_id=case_id, chunk_id=case_id + "_task", chunk_type="task",
                          text="ranking experience", module=module, final_status=status, source="CONV_TEST")


def _retriever(root, chunks, scores):
    """Build a controlled two-dimensional index without any external model."""
    vectors = np.array([[score, np.sqrt(1 - score ** 2)] for score in scores], dtype="float32")
    save_index(vectors, chunks, "mock", root)
    retriever = Retriever(index_dir=root, provider_name="mock")
    retriever.provider = SimpleNamespace(encode_query=lambda query: np.array([1, 0], dtype="float32"))
    return retriever


def test_success_bonus_is_applied_before_top_k(tmp_path):
    """A slightly lower cosine match must rise above a failed case after its bonus."""
    retriever = _retriever(tmp_path, [_chunk("CASE_FAILED", status="failed"), _chunk("CASE_SUCCESS")],
                           [1.0, 0.995])
    assert retriever.search("query", top_k=1)[0].case_id == "CASE_SUCCESS"
    assert retriever.search("query", top_k=1, prefer_success=False)[0].case_id == "CASE_FAILED"


def test_module_filter_does_not_drop_lower_scoring_matches(tmp_path):
    """A matching module beyond the old four-times-top-k window must remain retrievable."""
    chunks = [_chunk(f"CASE_{number}", module="Other") for number in range(20)]
    chunks.append(_chunk("CASE_TARGET", module="Ranking"))
    retriever = _retriever(tmp_path, chunks, [1.0] * 20 + [0.8])
    assert retriever.search("query", top_k=1, module="ranking")[0].case_id == "CASE_TARGET"


def test_score_rounding_does_not_change_rank(tmp_path):
    """Keep full similarity precision when close scores round to the same display value."""
    retriever = _retriever(tmp_path, [_chunk("CASE_A"), _chunk("CASE_Z")], [0.80001, 0.80002])
    assert retriever.search("query", top_k=1, prefer_success=False)[0].case_id == "CASE_Z"


def test_index_rejects_different_model_before_loading_it(tmp_path):
    """Reject same-dimension but different-model indices instead of silently misranking."""
    save_index(np.ones((1, 2), dtype="float32"), [_chunk("CASE_1")], "bge-m3",
               tmp_path, embedding_model="old-model")
    with patch("algo_rag_demo.rag.retriever.get_embedding_provider",
               side_effect=AssertionError("Should not load a model")):
        with pytest.raises(ValueError, match="rebuild"):
            Retriever(index_dir=tmp_path, provider_name="bge-m3", embedding_model="new-model")


def test_invalid_query_dimension_and_top_k_are_rejected(tmp_path):
    """Return useful errors instead of a low-level FAISS crash."""
    retriever = _retriever(tmp_path, [_chunk("CASE_1")], [1.0])
    with pytest.raises(ValueError, match="positive"):
        retriever.search("query", top_k=0)
    retriever.provider = SimpleNamespace(encode_query=lambda query: np.ones(3))
    with pytest.raises(ValueError, match="dimension"):
        retriever.search("query")


@pytest.mark.parametrize("field,value", [
    ("case_id", "../escape"), ("final_status", "maybe"), ("constraints", {"interface": "not a list"}),
])
def test_schema_rejects_invalid_user_data(field, value):
    """Verify real Pydantic rejects malformed case identifiers, statuses, and types."""
    data = read_json(Path("examples/custom_data/cases/CASE_CUSTOM_001.json"))
    data[field] = value
    with pytest.raises(ValidationError):
        EngineeringCase(**data)


def test_case_filename_must_match_identity(tmp_path):
    """Ensure reported case_path always points to the actual source file."""
    data = read_json(Path("examples/custom_data/cases/CASE_CUSTOM_001.json"))
    write_json(tmp_path / "CASE_OTHER.json", data)
    with pytest.raises(ValueError, match="filename"):
        load_cases(tmp_path)


def test_extraction_collision_does_not_overwrite_another_conversation(tmp_path):
    """Preserve earlier cases when an LLM returns the same id for different conversations."""
    raw = tmp_path / "raw"
    cases = tmp_path / "cases"
    for number in [1, 2]:
        write_json(raw / f"conversation_{number}.json", {
            "conversation_id": f"CONV_{number}", "task": "upgrade", "messages": [],
        })
    original = read_json(Path("examples/custom_data/cases/CASE_CUSTOM_001.json"))
    class Extractor:
        def extract(self, conversation):
            """Return intentionally colliding model identifiers."""
            return EngineeringCase(**dict(original, source_conversation_id=conversation.conversation_id))
    iterator = extract_case_directory(raw, cases, Extractor())
    next(iterator)
    with pytest.raises(ValueError, match="Duplicate"):
        next(iterator)
    assert read_json(cases / "CASE_CUSTOM_001.json")["source_conversation_id"] == "CONV_1"
    assert list(cases.glob("*.json")) == [cases / "CASE_CUSTOM_001.json"]


def test_bge_encodes_in_bounded_batches():
    """Prove document count cannot expand one inference batch without loading BGE."""
    encoder = object.__new__(BgeM3EmbeddingProvider)
    encoder.batch_size = 4
    sizes = []
    def encode_batch(texts):
        """Record batch sizes and return valid stand-in vectors."""
        sizes.append(len(texts))
        return np.ones((len(texts), 2), dtype="float32")
    encoder._encode_batch = encode_batch
    assert encoder._encode(["text"] * 10).shape == (10, 2)
    assert sizes == [4, 4, 2]


def test_preparation_failure_writes_final_report(tmp_path, monkeypatch):
    """Persist missing-key failures before index building or project edits."""
    args = cli.build_parser().parse_args(["run"])
    monkeypatch.setattr(cli, "_run_dir", lambda prefix: tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        cli.cmd_run(args)
    report = read_json(tmp_path / "final_report.json")
    assert report["status"] == "failed"
    assert report["attempts"] == []


def test_json_parser_accepts_fences_but_rejects_arrays():
    """Use the same strict model response parser for extraction and planning."""
    assert parse_json_object('```json\n{"plan": []}\n```') == {"plan": []}
    with pytest.raises(ValueError, match="object"):
        parse_json_object("[]")
    with pytest.raises(json.JSONDecodeError):
        parse_json_object('{"plan": []} {"unexpected": []}')


def test_project_copy_excludes_outputs_and_bytecode(tmp_path):
    """Copying a project containing the run directory must not recurse into itself."""
    source = tmp_path / "project"
    write_json(source / "config.json", {})
    (source / "__pycache__").mkdir()
    (source / "__pycache__/old.pyc").write_bytes(b"old")
    adapter = FileProjectAdapter({
        "template_dir": str(source), "allowed_files": ["config.json"],
        "validation_commands": [["{python}", "-c", "print('pass')"]],
    }, source / "outputs/runs/one")
    assert (adapter.workspace / "config.json").exists()
    assert not (adapter.workspace / "outputs").exists()
    assert not (adapter.workspace / "__pycache__").exists()


def test_validation_does_not_reuse_stale_bytecode(tmp_path):
    """Successive same-size edits in one second must execute the newest source."""
    import os
    source = tmp_path / "project"
    source.mkdir()
    (source / "value.py").write_text("value = 0\n", encoding="utf-8")
    adapter = FileProjectAdapter({
        "template_dir": str(source), "allowed_files": ["value.py"],
        "validation_commands": [["{python}", "-c", "from value import value; print(value)"]],
    }, tmp_path / "run")
    path = adapter.workspace / "value.py"
    stamp = path.stat().st_mtime
    assert adapter.validate()["checks"][0]["stdout"].strip() == "0"
    adapter.execute({"actions": [{"tool": "write_file", "path": "value.py", "content": "value = 1\n"}]})
    os.utime(path, (stamp, stamp))
    assert adapter.validate()["checks"][0]["stdout"].strip() == "1"
