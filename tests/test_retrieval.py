from algo_rag_demo.rag.index_builder import build_index
from algo_rag_demo.rag.retriever import Retriever


def test_retrieval_returns_dre_case():
    """Verify interface-compatible DRE queries retrieve the DRE case."""
    # Rebuilding the index makes the test independent of prior CLI runs.
    build_index("mock")
    results = Retriever(provider_name="mock").search("keep DRE downstream interface compatible", top_k=3)
    assert any(item.case_id == "CASE_DRE_001" for item in results)


def test_retrieval_ranking_distinguishes_case_types():
    """Verify targeted queries rank the intended case first."""
    # The mock embedding keywords are tuned to make these rankings stable.
    build_index("mock")
    retriever = Retriever(provider_name="mock")
    queries = {
        "missing metadata algorithm runtime evidence": "CASE_META_001",
        "pipeline json still selects old algorithm rollback": "CASE_CONFIG_001",
        "threshold calibration metric drift tolerance": "CASE_TUNING_001",
        "HWC CHW image shape layout mismatch": "CASE_DRE_002",
        "runtime dependency version mismatch crash": "CASE_RUNTIME_001",
    }
    for query, expected_case in queries.items():
        top = retriever.search(query, top_k=1)[0]
        assert top.case_id == expected_case

