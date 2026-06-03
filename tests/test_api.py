"""
Tests de integración para la API REST (FastAPI).

Usa el TestClient de FastAPI para probar los endpoints sin levantar
un servidor real. Los componentes externos (LLM, embeddings) se mockean
para evitar costos de tokens y dependencias de red.

Endpoints testeados:
- GET  /health  → Estado del servicio
- POST /ingest  → Re-ingesta de documentación
- POST /ask     → Pregunta con flujo RAG (mockeado)
"""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, _get_store


@pytest.fixture
def client():
    """TestClient de FastAPI para simular requests HTTP."""
    return TestClient(app)


# ── GET /health ────────────────────────────────────────────────────

class TestHealthEndpoint:
    """Tests para el endpoint GET /health."""

    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient):
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "ok"
        assert "indexed_chunks" in data
        assert isinstance(data["indexed_chunks"], int)

    def test_health_includes_version(self, client: TestClient):
        response = client.get("/health")
        data = response.json()
        assert "version" in data


# ── POST /ask ──────────────────────────────────────────────────────

class TestAskEndpoint:
    """Tests para el endpoint POST /ask con mocks del LLM y búsqueda."""

    @patch("src.api.main.generate_answer")
    @patch("src.api.main.embed_texts")
    @patch("src.api.main._get_store")
    def test_ask_returns_answer(
        self,
        mock_store_fn: MagicMock,
        mock_embed: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
    ):
        """El endpoint /ask devuelve una respuesta con fuentes y modelo."""
        # Configurar mocks
        mock_store = MagicMock()
        mock_store.count = 5
        mock_store.search.return_value = [
            MagicMock(
                text="Error de conexión con el servidor.",
                source_file="docs/test.txt",
                chunk_index=0,
                distance=0.3,
                metadata={},
            )
        ]
        mock_store_fn.return_value = mock_store

        mock_embed.return_value = [[0.1] * 384]

        mock_generate.return_value = {
            "answer": "El error de conexión se debe a que el servidor está apagado.",
            "model": "gpt-4o-mini",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }

        response = client.post(
            "/ask",
            json={"question": "Error de conexión a base de datos"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "model" in data
        assert len(data["answer"]) > 0

    @patch("src.api.main._get_store")
    def test_ask_no_docs_returns_503(
        self,
        mock_store_fn: MagicMock,
        client: TestClient,
    ):
        """Si no hay documentación indexada, devuelve 503."""
        mock_store = MagicMock()
        mock_store.count = 0
        mock_store_fn.return_value = mock_store

        response = client.post(
            "/ask",
            json={"question": "¿Cómo reinicio el servicio?"},
        )

        assert response.status_code == 503

    def test_ask_empty_question_returns_422(self, client: TestClient):
        """Una pregunta vacía devuelve 422 (validación Pydantic)."""
        response = client.post("/ask", json={"question": ""})
        assert response.status_code == 422

    def test_ask_missing_question_returns_422(self, client: TestClient):
        """Sin campo 'question' devuelve 422."""
        response = client.post("/ask", json={})
        assert response.status_code == 422

    @patch("src.api.main.generate_answer")
    @patch("src.api.main.embed_texts")
    @patch("src.api.main._get_store")
    def test_ask_llm_error_returns_502(
        self,
        mock_store_fn: MagicMock,
        mock_embed: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
    ):
        """Si el LLM falla, devuelve 502."""
        mock_store = MagicMock()
        mock_store.count = 5
        mock_store.search.return_value = [
            MagicMock(
                text="Texto de contexto",
                source_file="docs/test.txt",
                chunk_index=0,
                distance=0.2,
                metadata={},
            )
        ]
        mock_store_fn.return_value = mock_store
        mock_embed.return_value = [[0.1] * 384]
        mock_generate.side_effect = RuntimeError("OpenAI API: sin cuota")

        response = client.post(
            "/ask",
            json={"question": "¿Cómo soluciono el error?"},
        )

        assert response.status_code == 502

    @patch("src.api.main.generate_answer")
    @patch("src.api.main.embed_texts")
    @patch("src.api.main._get_store")
    def test_ask_sources_have_relevance(
        self,
        mock_store_fn: MagicMock,
        mock_embed: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
    ):
        """Las fuentes devueltas incluyen score de relevancia."""
        mock_store = MagicMock()
        mock_store.count = 5
        mock_store.search.return_value = [
            MagicMock(
                text="Chunk relevante",
                source_file="docs/test.txt",
                chunk_index=0,
                distance=0.25,
                metadata={},
            )
        ]
        mock_store_fn.return_value = mock_store
        mock_embed.return_value = [[0.1] * 384]
        mock_generate.return_value = {
            "answer": "Respuesta generada.",
            "model": "gpt-4o-mini",
        }

        response = client.post(
            "/ask",
            json={"question": "Pregunta de prueba"},
        )

        data = response.json()
        assert len(data["sources"]) == 1
        source = data["sources"][0]
        assert "relevance" in source
        assert 0 <= source["relevance"] <= 1
        assert "source_file" in source


# ── POST /ingest ───────────────────────────────────────────────────

class TestIngestEndpoint:
    """Tests para el endpoint POST /ingest."""

    @patch("src.api.main.VectorStore")
    @patch("src.api.main.run_ingestion")
    def test_ingest_returns_stats(
        self,
        mock_ingest: MagicMock,
        mock_vs_class: MagicMock,
        client: TestClient,
    ):
        """La ingesta devuelve estadísticas del procesamiento."""
        mock_stats = MagicMock()
        mock_stats.files_processed = 4
        mock_stats.files_skipped = 0
        mock_stats.total_chunks = 12
        mock_stats.total_indexed = 12
        mock_ingest.return_value = mock_stats

        response = client.post("/ingest")

        assert response.status_code == 200
        data = response.json()
        assert data["files_processed"] == 4
        assert data["total_indexed"] == 12
        assert "message" in data

    @patch("src.api.main.run_ingestion")
    def test_ingest_missing_docs_returns_404(
        self,
        mock_ingest: MagicMock,
        client: TestClient,
    ):
        """Si no existe la carpeta docs/, devuelve 404."""
        mock_ingest.side_effect = FileNotFoundError("docs/ no encontrado")

        response = client.post("/ingest")

        assert response.status_code == 404
