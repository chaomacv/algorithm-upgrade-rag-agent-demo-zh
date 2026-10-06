from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from algo_rag_demo.case_pipeline.chunker import chunk_cases
from algo_rag_demo.case_pipeline.schema import EngineeringCase, KnowledgeChunk, model_to_dict
from algo_rag_demo.config import CASE_DIR, INDEX_DIR, KNOWLEDGE_DIR
from algo_rag_demo.rag.embedding import EmbeddingProvider, get_embedding_provider
from algo_rag_demo.utils.jsonio import read_json, write_json


def load_cases(case_dir: Path = CASE_DIR) -> List[EngineeringCase]:
    """Load all structured case JSON files from disk."""
    # Sorting gives deterministic chunk and vector row order.
    return [EngineeringCase(**read_json(path)) for path in sorted(case_dir.glob("CASE_*.json"))]


def build_index(provider_name: str = "mock") -> Tuple[int, int, int]:
    """Build chunks, embeddings, and a FAISS-compatible index."""
    # chunks.json is kept as a readable audit artifact before vectorization.
    provider = get_embedding_provider(provider_name)
    cases = load_cases()
    chunks = chunk_cases(cases)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(KNOWLEDGE_DIR / "chunks.json", [model_to_dict(chunk) for chunk in chunks])
    texts = [chunk.text for chunk in chunks]
    vectors = provider.encode_documents(texts)
    save_index(vectors, chunks, provider_name)
    return len(cases), len(chunks), int(vectors.shape[1])


def save_index(vectors: np.ndarray, chunks: List[KnowledgeChunk], provider_name: str) -> None:
    """Persist vectors and metadata for later retrieval."""
    # Metadata maps vector row ids back to chunk and case identities.
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    metadata: Dict[str, Dict[str, object]] = {
        str(i): model_to_dict(chunk) for i, chunk in enumerate(chunks)
    }
    metadata["_provider"] = {"name": provider_name, "dimension": int(vectors.shape[1])}

    try:
        import faiss  # type: ignore

        index = faiss.IndexFlatIP(int(vectors.shape[1]))
        index.add(vectors.astype("float32"))
        faiss.write_index(index, str(INDEX_DIR / "cases.index"))
    except Exception:
        with (INDEX_DIR / "cases.index").open("wb") as handle:
            np.save(handle, vectors.astype("float32"))

    write_json(INDEX_DIR / "metadata.json", metadata)

