from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from algo_rag_demo.config import CASE_DIR, INDEX_DIR
from algo_rag_demo.rag.embedding import get_embedding_provider
from algo_rag_demo.rag.models import RetrievalResult
from algo_rag_demo.utils.jsonio import read_json


class Retriever:
    def __init__(
        self,
        index_dir: Path = INDEX_DIR,
        provider_name: str = "mock",
        embedding_model: str = None,
        case_dir: Path = CASE_DIR,
    ) -> None:
        """Load the vector index, metadata, and query embedding provider."""
        # Retrieval must use the same provider family that built the index.
        self.index_dir = index_dir
        # case_dir is stored so custom runs can point results back to user data.
        self.case_dir = case_dir
        self.metadata = read_json(index_dir / "metadata.json")
        expected_model = embedding_model or ("BAAI/bge-m3" if provider_name == "bge-m3" else None)
        saved = self.metadata["_provider"]
        if saved.get("name") != provider_name or saved.get("model") != expected_model:
            raise ValueError("Embedding provider/model differs from this index; rebuild the index first.")
        self.provider = get_embedding_provider(provider_name, model_name=embedding_model)
        self.index = self._load_index()

    def _load_index(self):
        """Load FAISS index when available, otherwise load NumPy fallback."""
        # The fallback keeps the demo runnable without faiss-cpu installed.
        path = self.index_dir / "cases.index"
        if self.metadata.get("_format") == "numpy":
            with path.open("rb") as handle:
                return np.load(handle, allow_pickle=False)
        if self.metadata.get("_format") == "faiss":
            import faiss  # type: ignore
            return faiss.read_index(str(path))
        raise ValueError("Legacy or unknown index format; rebuild the index first.")

    def search(
        self,
        query: str,
        top_k: int = 5,
        module: Optional[str] = None,
        prefer_success: bool = True,
    ) -> List[RetrievalResult]:
        """Search top matching chunks for one query."""
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        # Query and document vectors are normalized, so dot product ranks similarity.
        vector = self.provider.encode_query(query).reshape(1, -1).astype("float32")
        if vector.shape[1] != self.metadata["_provider"]["dimension"] or not np.isfinite(vector).all():
            raise ValueError("Query embedding dimension or values do not match the index.")
        # Filtering and success bonuses must be applied before selecting top-k.
        if hasattr(self.index, "search"):
            count = self.index.ntotal if module or prefer_success else min(top_k, self.index.ntotal)
            scores, ids = self.index.search(vector, count)
            pairs = list(zip(ids[0].tolist(), scores[0].tolist()))
        else:
            scores = np.dot(self.index, vector[0])
            ids = np.argsort(-scores)
            pairs = [(int(i), float(scores[i])) for i in ids]

        results: List[RetrievalResult] = []
        for idx, score in pairs:
            # Metadata turns a vector row id back into an explainable chunk.
            if idx < 0:
                continue
            meta: Dict[str, str] = self.metadata[str(idx)]
            if module and meta["module"].lower() != module.lower():
                continue
            adjusted = float(score)
            if prefer_success and meta["final_status"] == "success":
                adjusted += 0.01
            results.append(
                RetrievalResult(
                    score=adjusted,
                    case_id=meta["case_id"],
                    chunk_id=meta["chunk_id"],
                    chunk_type=meta["chunk_type"],
                    text=meta["text"],
                    module=meta["module"],
                    final_status=meta["final_status"],
                    source=meta["source"],
                    case_path=str(self.case_dir / f"{meta['case_id']}.json"),
                )
            )
        results.sort(key=lambda item: (-item.score, item.chunk_id))
        return results[:top_k]

