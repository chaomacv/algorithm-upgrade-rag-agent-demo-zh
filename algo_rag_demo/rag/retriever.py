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
        case_dir: Path = CASE_DIR,
    ) -> None:
        """Load the vector index, metadata, and query embedding provider."""
        # Retrieval must use the same provider family that built the index.
        self.index_dir = index_dir
        # case_dir is stored so custom runs can point results back to user data.
        self.case_dir = case_dir
        self.provider = get_embedding_provider(provider_name)
        self.metadata = read_json(index_dir / "metadata.json")
        self.index = self._load_index()

    def _load_index(self):
        """Load FAISS index when available, otherwise load NumPy fallback."""
        # The fallback keeps the demo runnable without faiss-cpu installed.
        path = self.index_dir / "cases.index"
        try:
            import faiss  # type: ignore

            return faiss.read_index(str(path))
        except Exception:
            with path.open("rb") as handle:
                return np.load(handle)

    def search(
        self,
        query: str,
        top_k: int = 5,
        module: Optional[str] = None,
        prefer_success: bool = True,
    ) -> List[RetrievalResult]:
        """Search top matching chunks for one query."""
        # Query and document vectors are normalized, so dot product ranks similarity.
        vector = self.provider.encode_query(query).reshape(1, -1).astype("float32")
        if hasattr(self.index, "search"):
            scores, ids = self.index.search(vector, min(top_k * 4, self.index.ntotal))
            pairs = list(zip(ids[0].tolist(), scores[0].tolist()))
        else:
            scores = np.dot(self.index, vector[0])
            ids = np.argsort(-scores)[: top_k * 4]
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
                    score=round(adjusted, 4),
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
            if len(results) >= top_k:
                break
        return results

