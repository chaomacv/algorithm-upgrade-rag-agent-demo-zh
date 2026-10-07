import hashlib
import os
from typing import List, Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    def encode_documents(self, texts: List[str]) -> np.ndarray:
        """Encode multiple corpus texts into normalized vectors."""
        ...

    def encode_query(self, text: str) -> np.ndarray:
        """Encode one query text into a normalized vector."""
        ...


class MockEmbeddingProvider:
    """Deterministic embedding for tests and offline smoke runs.

    It combines keyword features with hash features. This is intentionally not a
    semantic embedding model; it only makes the demo reproducible without a model
    download or API key.
    """

    def __init__(self, dimension: int = 64) -> None:
        """Create deterministic keyword/hash feature space."""
        self.dimension = dimension
        self.keywords = [
            "algorithm",
            "module",
            "ranking",
            "ranker",
            "scorer",
            "legacyranker",
            "neuralscorer",
            "interface",
            "downstream",
            "compatible",
            "compatibility",
            "schema",
            "contract",
            "runtime",
            "config",
            "rollback",
            "shape",
            "dependency",
            "version",
            "switch",
            "metadata",
            "confidence",
            "reason",
            "observability",
            "configuration",
            "validation",
            "adapter",
            "evidence",
            "root_cause",
            "solution",
            "migration",
        ]

    def encode_documents(self, texts: List[str]) -> np.ndarray:
        """Encode every document with the deterministic mock encoder."""
        # Stacking keeps the return shape compatible with real embedding models.
        return np.vstack([self._encode(text) for text in texts]).astype("float32")

    def encode_query(self, text: str) -> np.ndarray:
        """Encode one query with the deterministic mock encoder."""
        return self._encode(text).astype("float32")

    def _encode(self, text: str) -> np.ndarray:
        """Build a normalized keyword/hash vector for one text."""
        # Keyword dimensions make demo ranking understandable and stable.
        vector = np.zeros(self.dimension, dtype="float32")
        normalized = text.lower().replace("-", "_")
        for idx, keyword in enumerate(self.keywords):
            if keyword in normalized:
                vector[idx] += 5.0
        for token in normalized.replace("/", " ").replace(".", " ").split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = 16 + digest[0] % (self.dimension - 16)
            vector[bucket] += 0.05
        norm = float(np.linalg.norm(vector))
        if norm == 0:
            vector[0] = 1.0
            norm = 1.0
        return vector / norm


class BgeM3EmbeddingProvider:
    """BAAI/bge-m3 dense embedding provider using Transformers."""

    def __init__(self, model_name: str = "BAAI/bge-m3", max_length: int = 8192) -> None:
        """Load BGE-M3 locally and choose GPU when PyTorch can see CUDA."""
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModel, AutoTokenizer

        resolved_model_path = model_name
        if not os.path.exists(model_name):
            # Download only the files needed for PyTorch inference; some mirrors
            # reject auxiliary repository artifacts such as imgs/.DS_Store.
            resolved_model_path = snapshot_download(
                repo_id=model_name,
                ignore_patterns=[
                    "imgs/*",
                    "*.DS_Store",
                    "*/.DS_Store",
                    "*.onnx",
                    "*.onnx_data",
                    "onnx/*",
                    "flax_model.msgpack",
                    "rust_model.ot",
                    "tf_model.h5",
                ],
            )

        self.torch = torch
        self.max_length = max_length
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(resolved_model_path)
        self.model = AutoModel.from_pretrained(resolved_model_path).to(self.device)
        self.model.eval()

    def encode_documents(self, texts: List[str]) -> np.ndarray:
        """Encode corpus texts with BGE-M3 dense embeddings."""
        return self._encode(texts)

    def encode_query(self, text: str) -> np.ndarray:
        """Encode one query with BGE-M3 dense embeddings."""
        return self._encode([text])[0]

    def _encode(self, texts: List[str]) -> np.ndarray:
        """Run BGE-M3 and L2-normalize dense vectors."""
        # The first-token embedding is the standard dense vector interface for
        # BGE encoder models; normalization makes inner product behave like cosine.
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        with self.torch.no_grad():
            output = self.model(**encoded)
            vectors = output.last_hidden_state[:, 0].detach().cpu().numpy().astype("float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


def get_embedding_provider(name: str = "mock", model_name: str = None) -> EmbeddingProvider:
    """Select the configured embedding provider by name."""
    # Keep provider selection centralized for CLI and retriever consistency.
    if name == "bge-m3":
        return BgeM3EmbeddingProvider(model_name or "BAAI/bge-m3")
    if name == "mock":
        return MockEmbeddingProvider()
    raise ValueError(f"Unknown embedding provider: {name}")

