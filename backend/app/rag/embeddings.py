"""Embedding provider abstraction.

Anthropic does not serve an embeddings endpoint, so NAVI treats embeddings as a
pluggable dependency. In production, point this at Voyage AI (Anthropic's
recommended embeddings partner) or any other provider by implementing
`EmbeddingProvider`. A deterministic local fallback is included so the
retrieval pipeline is runnable end-to-end without an extra API key.
"""

import hashlib
import os
from abc import ABC, abstractmethod

from app.models.document_chunk import EMBEDDING_DIM


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class VoyageEmbeddingProvider(EmbeddingProvider):
    """Wraps the Voyage AI embeddings API (voyage-3, healthcare-tuned models available)."""

    def __init__(self, api_key: str, model: str = "voyage-3"):
        import voyageai  # imported lazily so the dependency is optional

        self._client = voyageai.Client(api_key=api_key)
        self._model = model

    def embed(self, text: str) -> list[float]:
        result = self._client.embed([text], model=self._model, input_type="document")
        return result.embeddings[0]


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Deterministic, dependency-free fallback for local development and demos.

    NOT semantically meaningful beyond crude lexical overlap — swap in
    VoyageEmbeddingProvider (or similar) before relying on this for real
    similarity search.
    """

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
            vector[index] += 1.0
        norm = sum(v * v for v in vector) ** 0.5
        return [v / norm for v in vector] if norm else vector


def get_embedding_provider() -> EmbeddingProvider:
    voyage_key = os.getenv("VOYAGE_API_KEY")
    if voyage_key:
        return VoyageEmbeddingProvider(api_key=voyage_key)
    return LocalHashEmbeddingProvider()
