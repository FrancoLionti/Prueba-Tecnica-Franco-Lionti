"""
Métricas light de observabilidad para el endpoint /ask.

Registra en logs estructurados (JSON) las latencias y tamaños
de cada etapa del flujo RAG, sin dependencias externas.

En producción esto se conectaría a una plataforma de observabilidad
(Langfuse, Datadog, etc.) pero aquí demostramos el patrón base
de instrumentación que alimenta esas plataformas.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from typing import Generator

# ── Logger estructurado ────────────────────────────────────────────
# Formato JSON para facilitar la ingestión en plataformas de logs
# (ELK, CloudWatch, Datadog, etc.)
logger = logging.getLogger("rag.metrics")


@dataclass
class RequestMetrics:
    """Métricas recolectadas durante una request a /ask."""

    # Latencias (en milisegundos)
    embedding_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    total_latency_ms: float = 0.0

    # Tamaños (proxy de tokens — los tokens exactos se obtienen
    # del response de OpenAI, pero los caracteres sirven como
    # métrica rápida sin parsear la respuesta del proveedor)
    question_chars: int = 0
    context_chars: int = 0
    answer_chars: int = 0

    # Retrieval
    chunks_retrieved: int = 0
    top_relevance: float = 0.0

    # LLM
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        """Serializa las métricas para logging."""
        return asdict(self)

    def log(self) -> None:
        """Emite un log estructurado con todas las métricas."""
        logger.info(
            "rag_request_metrics",
            extra={"metrics": self.to_dict()},
        )


@contextmanager
def measure(label: str) -> Generator[dict, None, None]:
    """
    Context manager que mide el tiempo de un bloque de código.

    Uso:
        with measure("retrieval") as timing:
            results = store.search(...)
        print(timing["elapsed_ms"])  # → 12.34
    """
    result: dict = {"elapsed_ms": 0.0}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["elapsed_ms"] = round(
            (time.perf_counter() - start) * 1000, 2
        )
