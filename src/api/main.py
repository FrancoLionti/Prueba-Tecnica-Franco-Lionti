"""
FastAPI application — API REST del asistente de soporte.

Endpoints:
- POST /ask     → Recibe una pregunta y devuelve una respuesta contextual
- POST /ingest  → Re-procesa la documentación y actualiza el vector store
- GET  /health  → Estado del servicio
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from src.api.metrics import RequestMetrics, measure
from src.api.schemas import (
    AnswerResponse,
    HealthResponse,
    IngestResponse,
    QuestionRequest,
    SourceChunk,
)
from src.config import RETRIEVAL_MIN_RELEVANCE, RETRIEVAL_TOP_K
from src.ingestion.embedder import embed_texts
from src.ingestion.pipeline import run_ingestion
from src.ingestion.vector_store import VectorStore
from src.llm.generator import generate_answer

# ── Logging ────────────────────────────────────────────────────────
logger = logging.getLogger("rag.api")

# ── Singleton del vector store ─────────────────────────────────────
# Se inicializa una vez al arrancar y se reutiliza en todos los requests.
_store: VectorStore | None = None


def _get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


# ── Lifecycle ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos al arrancar y los libera al apagar."""
    # Startup: pre-cargar el vector store
    _get_store()
    print(f"Vector store listo — {_get_store().count} chunks indexados")
    yield
    # Shutdown
    print("Apagando API...")


# ── App ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Asistente de Soporte RAG",
    description="API REST que responde preguntas de soporte "
                "usando documentación técnica interna.",
    version="0.1.0",
    lifespan=lifespan,
)


# ── POST /ask ──────────────────────────────────────────────────────
@app.post("/ask", response_model=AnswerResponse)
async def ask_question(body: QuestionRequest):
    """
    Recibe una pregunta del usuario y devuelve una respuesta
    generada por el LLM basándose en la documentación indexada.

    Flujo: pregunta → embedding → búsqueda en ChromaDB → contexto → LLM → respuesta
    """
    metrics = RequestMetrics(question_chars=len(body.question))
    store = _get_store()

    if store.count == 0:
        raise HTTPException(
            status_code=503,
            detail="No hay documentación indexada. Ejecutar POST /ingest primero.",
        )

    # 1. Generar embedding de la pregunta
    with measure("embedding") as emb_t:
        query_embedding = embed_texts([body.question])[0]
    metrics.embedding_latency_ms = emb_t["elapsed_ms"]

    # 2. Buscar los chunks más relevantes
    with measure("retrieval") as ret_t:
        results = store.search(query_embedding, top_k=RETRIEVAL_TOP_K)
    metrics.retrieval_latency_ms = ret_t["elapsed_ms"]

    # 3. Componer las fuentes con su score de relevancia y filtrar por relevancia mínima
    sources = [
        SourceChunk(
            text=r.text,
            source_file=r.source_file,
            relevance=round(1 - r.distance, 4),
        )
        for r in results
    ]
    
    # Filtrar chunks que no alcanzan el umbral de relevancia mínima
    sources = [s for s in sources if s.relevance >= RETRIEVAL_MIN_RELEVANCE]

    if not sources:
        return AnswerResponse(
            answer="No encontré información lo suficientemente relevante en la documentación para responder a tu pregunta.",
            sources=[],
            model="none",
        )

    metrics.chunks_retrieved = len(sources)
    metrics.top_relevance = max(s.relevance for s in sources)

    # 4. Preparar contexto para el LLM
    context_chunks = [
        {"text": s.text, "source_file": s.source_file}
        for s in sources
    ]
    metrics.context_chars = sum(len(c["text"]) for c in context_chunks)

    # 5. Generar respuesta del LLM
    try:
        with measure("llm") as llm_t:
            llm_result = generate_answer(
                question=body.question,
                context_chunks=context_chunks,
            )
        metrics.llm_latency_ms = llm_t["elapsed_ms"]
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 6. Completar métricas
    answer_text = llm_result["answer"]
    metrics.answer_chars = len(answer_text)
    metrics.model = llm_result.get("model", "")
    metrics.total_latency_ms = round(
        metrics.embedding_latency_ms
        + metrics.retrieval_latency_ms
        + metrics.llm_latency_ms,
        2,
    )

    usage = llm_result.get("usage", {})
    metrics.prompt_tokens = usage.get("prompt_tokens", 0)
    metrics.completion_tokens = usage.get("completion_tokens", 0)
    metrics.total_tokens = usage.get("total_tokens", 0)

    # 7. Emitir log estructurado de métricas
    metrics.log()

    return AnswerResponse(
        answer=answer_text,
        sources=sources,
        model=metrics.model,
        metrics=metrics.to_dict(),
    )


# ── POST /ingest ───────────────────────────────────────────────────
@app.post("/ingest", response_model=IngestResponse)
async def ingest_docs():
    """
    Re-procesa toda la documentación en /docs y actualiza el vector store.
    Limpia los embeddings previos para evitar duplicados.
    """
    global _store

    try:
        stats = run_ingestion(clear_existing=True)
        # Refrescar el store después de la re-ingesta
        _store = VectorStore()

        return IngestResponse(
            files_processed=stats.files_processed,
            files_skipped=stats.files_skipped,
            total_chunks=stats.total_chunks,
            total_indexed=stats.total_indexed,
            message=f"Ingesta completada: {stats.total_indexed} chunks indexados.",
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en ingesta: {e}")


# ── GET /health ────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica que el servicio esté funcionando."""
    store = _get_store()
    return HealthResponse(
        status="ok",
        indexed_chunks=store.count,
    )
