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
    # The default index uses the repository's bundled synthetic examples.
    return build_index_from_cases(
        provider_name=provider_name,
        case_dir=CASE_DIR,
        knowledge_dir=KNOWLEDGE_DIR,
        index_dir=INDEX_DIR,
    )


def build_index_from_cases(
    provider_name: str = "mock",
    case_dir: Path = CASE_DIR,
    knowledge_dir: Path = KNOWLEDGE_DIR,
    index_dir: Path = INDEX_DIR,
) -> Tuple[int, int, int]:
    """Build chunks, embeddings, and an index from a caller-selected case directory."""
    # Custom runs pass their own case, knowledge, and index directories here so
    # generated artifacts stay separate from the bundled teaching demo.
    provider = get_embedding_provider(provider_name)
    cases = load_cases(case_dir)
    if not cases:
        raise ValueError(f"No CASE_*.json files found in {case_dir}")
    chunks = chunk_cases(cases)
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    write_json(knowledge_dir / "chunks.json", [model_to_dict(chunk) for chunk in chunks])
    texts = [chunk.text for chunk in chunks]
    vectors = provider.encode_documents(texts)
    save_index(vectors, chunks, provider_name, index_dir)
    return len(cases), len(chunks), int(vectors.shape[1])


def save_index(
    vectors: np.ndarray,
    chunks: List[KnowledgeChunk],
    provider_name: str,
    index_dir: Path = INDEX_DIR,
) -> None:
    """Persist vectors and metadata for later retrieval."""
    # Metadata maps vector row ids back to chunk and case identities.
    index_dir.mkdir(parents=True, exist_ok=True)
    metadata: Dict[str, Dict[str, object]] = {
        str(i): model_to_dict(chunk) for i, chunk in enumerate(chunks)
    }
    metadata["_provider"] = {"name": provider_name, "dimension": int(vectors.shape[1])}

    try:
        import faiss  # type: ignore

        index = faiss.IndexFlatIP(int(vectors.shape[1]))
        index.add(vectors.astype("float32"))
        faiss.write_index(index, str(index_dir / "cases.index"))
    except Exception:
        with (index_dir / "cases.index").open("wb") as handle:
            np.save(handle, vectors.astype("float32"))

    write_json(index_dir / "metadata.json", metadata)

