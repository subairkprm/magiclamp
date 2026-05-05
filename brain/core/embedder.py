"""
MagicLamp Embedding Layer

Provides a pluggable interface for generating dense vector embeddings used by
the RAG retrieval pipeline. Two concrete providers are shipped:

* ``LocalEmbedder``  — uses ``sentence-transformers`` running in-process. The
  default model (``all-MiniLM-L6-v2``, 384 dim) is already pre-downloaded in
  ``brain/Dockerfile``. The underlying model object is held as a module-level
  singleton so it is loaded at most once per process.
* ``OllamaEmbedder`` — calls Ollama's ``/api/embeddings`` endpoint, reusing
  ``settings.OLLAMA_URL`` and the existing ``ollama_circuit`` circuit breaker.

The provider is selected via ``settings.EMBEDDING_PROVIDER`` (``local`` |
``ollama``). Tests can swap the singleton via :func:`set_embedder`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Lock
from typing import List, Optional

import httpx

from core.config import settings
from core.logger import get_logger

log = get_logger("embedder")


class Embedder(ABC):
    """Abstract dense-vector embedding provider."""

    #: Output dimensionality. Must match the configured vector store.
    dim: int = 0

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Embed a single string and return a list of floats."""

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed many strings. Default impl loops; subclasses may batch."""
        return [self.embed(t) for t in texts]


# ── LOCAL (sentence-transformers) ─────────────────────────────────
_local_model = None
_local_lock = Lock()


def _get_sentence_transformer(model_name: str):
    """Lazy module-level singleton for the SentenceTransformer model."""
    global _local_model
    if _local_model is not None:
        return _local_model
    with _local_lock:
        if _local_model is None:
            # Imported lazily so test environments that swap in a FakeEmbedder
            # never need sentence-transformers installed.
            from sentence_transformers import SentenceTransformer  # type: ignore

            log.info(f"Loading local embedding model: {model_name}")
            _local_model = SentenceTransformer(model_name)
    return _local_model


class LocalEmbedder(Embedder):
    """In-process sentence-transformers embedder."""

    def __init__(self, model_name: Optional[str] = None, dim: Optional[int] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dim = dim or settings.EMBEDDING_DIM

    def embed(self, text: str) -> List[float]:
        model = _get_sentence_transformer(self.model_name)
        vec = model.encode(text, normalize_embeddings=True)
        return [float(x) for x in vec.tolist()]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = _get_sentence_transformer(self.model_name)
        vecs = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [[float(x) for x in v.tolist()] for v in vecs]


# ── OLLAMA ────────────────────────────────────────────────────────
class OllamaEmbedder(Embedder):
    """Embedder backed by Ollama's ``/api/embeddings`` endpoint."""

    def __init__(self, model_name: Optional[str] = None, dim: Optional[int] = None,
                 base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dim = dim or settings.EMBEDDING_DIM
        self.base_url = base_url or settings.OLLAMA_URL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT

    def embed(self, text: str) -> List[float]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
            )
            r.raise_for_status()
            data = r.json()
        # Ollama returns {"embedding": [...]}
        return [float(x) for x in data.get("embedding", [])]


# ── SINGLETON ─────────────────────────────────────────────────────
_embedder: Optional[Embedder] = None
_embedder_lock = Lock()


def _build_embedder() -> Embedder:
    provider = (settings.EMBEDDING_PROVIDER or "local").lower()
    if provider == "ollama":
        log.info("Using OllamaEmbedder")
        return OllamaEmbedder()
    if provider != "local":
        log.warning(f"Unknown EMBEDDING_PROVIDER '{provider}', falling back to 'local'")
    log.info("Using LocalEmbedder")
    return LocalEmbedder()


def get_embedder() -> Embedder:
    """Return the process-wide :class:`Embedder` singleton."""
    global _embedder
    if _embedder is not None:
        return _embedder
    with _embedder_lock:
        if _embedder is None:
            _embedder = _build_embedder()
    return _embedder


def set_embedder(embedder: Optional[Embedder]) -> None:
    """Override the embedder singleton (primarily for tests)."""
    global _embedder
    _embedder = embedder
