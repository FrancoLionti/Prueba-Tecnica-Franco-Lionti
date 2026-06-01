"""
Modelos Pydantic para request/response de la API.

Pydantic valida automáticamente los datos entrantes y genera
documentación OpenAPI (Swagger) a partir de los tipos definidos.
"""

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Body del POST /ask."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Pregunta del usuario sobre la documentación.",
        examples=["¿Cómo reinicio el servicio de autenticación?"],
    )


class SourceChunk(BaseModel):
    """Fragmento de documentación usado como fuente de la respuesta."""
    text: str
    source_file: str
    relevance: float = Field(
        description="Score de similitud (0-1, mayor = más relevante)."
    )


class AnswerResponse(BaseModel):
    """Respuesta del endpoint /ask."""
    answer: str = Field(description="Respuesta generada por el LLM.")
    sources: list[SourceChunk] = Field(
        default_factory=list,
        description="Fragmentos de documentación usados como contexto.",
    )
    model: str = Field(
        default="",
        description="Modelo de LLM utilizado para generar la respuesta.",
    )


class IngestResponse(BaseModel):
    """Respuesta del endpoint /ingest."""
    files_processed: int
    files_skipped: int
    total_chunks: int
    total_indexed: int
    message: str


class HealthResponse(BaseModel):
    """Respuesta del endpoint /health."""
    status: str
    indexed_chunks: int
    version: str = "0.1.0"
