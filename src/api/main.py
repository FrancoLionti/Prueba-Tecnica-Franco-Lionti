"""
FastAPI application — API REST del asistente de soporte.

Endpoints:
- POST /ask     → Recibe una pregunta y devuelve una respuesta contextual
- POST /ingest  → Re-procesa la documentación y actualiza el vector store
- GET  /health  → Estado del servicio
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from src.api.schemas import (
    AnswerResponse,
    HealthResponse,
    IngestResponse,
    QuestionRequest,
    SourceChunk,
)
from src.config import RETRIEVAL_TOP_K
from src.ingestion.embedder import embed_texts
from src.ingestion.pipeline import run_ingestion
from src.ingestion.vector_store import VectorStore


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
    basada en la documentación indexada.

    Por ahora (Fase 4) devuelve los fragmentos relevantes sin
    pasar por el LLM. En la Fase 5 se agrega la generación.
    """
    store = _get_store()

    if store.count == 0:
        raise HTTPException(
            status_code=503,
            detail="No hay documentación indexada. Ejecutar POST /ingest primero.",
        )

    # Generar embedding de la pregunta
    query_embedding = embed_texts([body.question])[0]

    # Buscar los chunks más relevantes
    results = store.search(query_embedding, top_k=RETRIEVAL_TOP_K)

    if not results:
        return AnswerResponse(
            answer="No se encontró información relevante en la documentación.",
            sources=[],
            model="none",
        )

    # Armar las fuentes con su score de relevancia
    sources = [
        SourceChunk(
            text=r.text,
            source_file=r.source_file,
            # Convertir distancia coseno a similitud (1 - distancia)
            relevance=round(1 - r.distance, 4),
        )
        for r in results
    ]

    # Fase 4: respuesta provisional con los fragmentos encontrados.
    # En la Fase 5 esto se reemplaza por la respuesta del LLM.
    context_preview = "\n---\n".join(
        f"[{s.source_file}] (relevancia: {s.relevance})\n{s.text}"
        for s in sources
    )

    return AnswerResponse(
        answer=f"[Fase 4 — Sin LLM] Contexto recuperado:\n\n{context_preview}",
        sources=sources,
        model="retrieval-only",
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
